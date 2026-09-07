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

  `toolkit/schema/test_smsgnames.py` (the eight opcode names the 2026-08-17 Factions
  captures earned, checked against the WIRE rather than against themselves. Section 1
  pins each row in `schema/overrides.json` -- name, `high` confidence, a citation to
  `studies/newopcodes/FINDINGS.md`, and NO field claim, since these are name-only rows.
  Section 2 is the half that can actually go red: every invariant is re-derived from the
  decrypted captures, so a name that stopped describing the traffic would fail. `0x011A
  TOWN_ALLIANCE_OBJECT` must carry two strings in all 126 sightings AND its key must
  stand in a BIJECTION with the guild name -- 18 keys, 18 (key,name) pairs, each
  announced 7 times, one per channel. **That check replaced one that failed for the wrong
  reason**: the first version asked how many first fields collided with a created agent
  id, scored 63/126, and reddened -- which is what coincidence looks like when small
  integers meet a 116-agent id space, not evidence about the name. Agent-keying is now
  refuted the discriminating way, since players sharing a guild would put one name under
  many keys. `0x00C4 WINDOW_OWNER`'s argument must be a live agent; `0x00F5 TITLE_UPDATE`
  must only name tracks `0x00F6 TITLE_TRACK_INFO` declared; `0x017E` STOP must never
  outnumber `0x0180`. Two sabotages built and run -- renaming `0x011A` back to the
  refuted `GUILD_LADDER_ENTRY`, and breaking the bijection -- and both redden. Needs the
  vault; declares a LEDGER.skip when the captures are absent rather than scoring zero.
  15 checks, ~20 s),
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
  test so the extraction is checked without crashing a client. **And since
  2026-08-18 it checks that capturing the dialog RETRACTS THE VERDICT**, which is a
  different thing and was not true: `hold_open` has returned `"exited"` for a client
  that died during the hold since `276080a`, and the comment at that `return` says
  *"a corpse afterwards unmakes it"* — but the only call site was a **bare expression
  statement**, `ok` was never reassigned after it, and such a run still printed
  `RUN VERDICT: PASS` and exited 0. `customarea/FINDINGS.md` §31.4 recorded the
  defect as fixed on the strength of that `return`; the statement shipped and the
  wiring did not. The rule now lives in `session.verdict_after_hold(ok, held)` with a
  three-row truth table here (a corpse retracts a pass, a hold that merely ran out
  does not, and it never PROMOTES a failed run), **plus a structural check that
  `run_client` actually consumes `hold_open`'s return** — because a correct helper
  nobody invokes is precisely the bug being fixed and looks identical from the
  outside. That structural check is the one that was red when the defect was found,
  and its own control parses the pre-fix shape verbatim and requires the detector to
  call it broken. Also `hold_key`,
  the held movement key `--walk` drives, against a fake `user32`: that every
  event carries a NON-ZERO scan code, that the key is released on every exit
  path including an exception mid-hold, that losing the foreground cuts the leg
  short, and that a client without focus gets nothing at all. Section 10 also
  pins the 2026-08-17 camera verbs — `yaw:N`, named-key holds (`alt:4`,
  `left:2`; ALT is nameplates), `shot:1` on the plan's own clock — parse and
  refuse correctly, with the named VKs asserted against LITERALS; together
  they retire "the harness cannot aim" for everything but a world-anchored
  click (validated live, harness 20260817T151242: zoom, two yaws, an ALT hold
  and three scripted shots all delivered). The 2026-08-19 `hover:FX,FY,SECS`
  verb (cursor park over a window-relative point, never a click — a HUD
  tooltip is the only readable surface for some state) parses and refuses in
  the same section: two numbers, a zero duration, an on-or-off-window
  fraction and a non-number all fail loudly, because a cursor parked at a
  wrong literal reads as "no tooltip", which is the probe's null result
  (validated live, harness 20260819T233451: a 38 s hover delivered all three
  effect tooltips of the buff_type_field probe). The scan code is
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
  `toolkit/harness/test_preflight_owner.py` (the `--replace` OWNERSHIP gate,
  added 2026-08-20 after the pre-flight's "is the listener python" test matched
  a PARALLEL session's live stack at ~23:00 and killed its webgate (pid 18520)
  and authsrv (pid 8412) mid-run — under one-worktree-per-session, another
  session's stack is indistinguishable from our stale one by image name.
  `--replace` now reads the listener's command line (pure ctypes:
  `NtQueryInformationProcess(ProcessCommandLineInformation)` +
  `CommandLineToArgvW`) and stops it only when the script it names resolves
  into THIS session's tree; the refusal prints the other listener's tree so the
  operator knows which session to coordinate with. The load-bearing check is
  refused-AND-ALIVE: a real listener started from a stand-in foreign worktree
  survives a `--replace` pre-flight that names its tree, while a real webgate
  from this tree still dies — the design intent has to survive the fix. Tree
  identity is nearest-`.git`-ancestor (a worktree's `.git` is a FILE), never a
  path prefix, and the nesting-trap check is why: worktrees live UNDER the
  main checkout, so a prefix test would call every worktree's stack the main
  session's own — the same kill through a different door. `this_tree()` is
  cross-checked against `git rev-parse --show-toplevel`'s own answer, the one
  check that may skip (floor 29, measured 30). Everything unprovable refuses:
  an unreadable command line, no script token, a RELATIVE script path (a
  hand-run three-terminal server's cwd is invisible). Section 6 settles the
  same evening's other question as executable fact rather than a reading of
  the code: the gamesrv alias IS pre-flighted — a squatter parked on 127.0.0.3
  at the gamesrv's port is refused before anything starts, and an AST check
  pins `main()` handing `preflight` the WHOLE un-narrowed `server_specs()`
  list, hops included. Every check runs on ephemeral ports so it can run
  beside a live session),
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
  **The header-refusal section added 2026-08-17, floor 78 -> 87.** File offsets
  `[0x00,0x10)` -- magic, `headerSize`, `blockSize` and the CRC covering them --
  are the ONE corruption with no recovery path: the client's header gate returns
  0 from a tail with no log call and tail-jumps to `ArchiveCreate`, which writes
  a fresh empty archive over the whole file. This module had no caller that wrote
  there, so the region was protected by ABSENCE, which is luck rather than
  protection. `Writer.put` now refuses it outright, and the test REACHES FOR IT
  at every field and at both sides of the `0x0F`/`0x10` boundary -- the pair that
  catches a half-open interval written as containment -- each attempt on its own
  fresh fixture, because the CONTROL is a permitted write and permitted writes
  are still destructive.
  **Section 7 (2026-08-14) is `--restore`, the IN-PLACE GROW `datmove.plan_move`
  names and refuses** -- its own docstring ends *"write the in-place grow as its
  own verb with its own test"*, and this is that verb. It puts a row back from a
  DONOR ARCHIVE rather than from a journal, which is the whole design: `--revert`
  expires the moment a client runs (the MFT moves, FINDINGS 4c) **and a journal is
  a file somebody has to still have** -- 127 icon rows were left armed in
  `vault/run/reskin-roster/` on the recorded understanding that their originals
  were "recoverable from the journals' `before` fields", and NO SUCH JOURNAL
  EXISTS anywhere in the vault. A pristine copy cannot go missing that way, and
  two of them agree byte-for-byte. Three things `--replace` could not do when this
  section was written, and each is a check -- **two of the three have since become
  verbs and only the third still holds**: it wrote **compression 0** and there was
  no compressor (superseded 2026-08-18 -- `--compression 8 --expect`, the gwenc
  arm); it computed the reservation from the row's CURRENT size, so a shrunk row
  could never grow back (2,068 B reserves 2,560 when the original needs 7,680)
  even though the blocks were never handed to anyone (superseded 2026-08-19 --
  `--grow-to`, section 11, which is exactly this refusal becoming a verb);
  and `--overwrite` is same-length only, which stands. The donor's WHOLE RESERVATION is copied,
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
  exactly. No vault, no client.
  **Sections 9 and 10 (2026-08-18) are the COMPRESSION-8 WRITE VERB and the C-6
  guard, floor 87 -> 136.** Until `gwenc.py` existed nothing in this project
  could produce compression-8 bytes, so `replace()` hardcoded the field to 0;
  it is now a keyword argument whose default reproduces the old behaviour byte
  for byte, because `iconset`, `rebloat`, `textwrite`, `deploy.py`'s subprocess
  and the six `a4stage*.py` staging scripts under `vault/research/archivewrite/`
  all depend on "it marks the row stored" and none of them is edited. Section 9
  is the whole pipeline of studies/archivewrite FINDINGS **A8 minus the client**:
  payload -> `gwenc.encode` -> the verb -> a FRESH `Archive.read()` ->
  unmodified `gwdat.decompress` -> the same payload, with the row afterwards
  saying compression 8, the STORED length, and a crc over the stored bytes (the
  domain FINDINGS 1.1 measured on retail's own comp-8 rows). It runs on
  **`test_datcheck`'s fixture, not this file's** -- this file's payload rows sit
  below `INDEX_FIRST_FILE = 16`, so `datcheck.preflight` is permanently 9/10 on
  it and a "ten open-time rules pass" claim could not be made honestly
  (measured both ways: 9/10 here, 10/10 there). **Section 9d is the
  load-bearing one and it asserts a DEFECT**: it stages FINDINGS C-6 on purpose
  -- correct compressed bytes with the code poked back to 0, self-crc repaired
  -- and measures that all ten open-time rules, the crc sweep and all three
  checksum rules stay GREEN over a file that no longer reads. That is why the
  verb decompresses and compares against a MANDATORY declared payload *before*
  the first byte is written: nothing this project owns can refute a
  conforming-but-wrong compressed row afterwards, and `datcheck.py` has no
  notion of a compression code at all. The corruptions that test the arm are
  **earned, not staged** -- one flipped bit inside a real compressed payload
  (which decodes to the right LENGTH without raising, so only a byte comparison
  sees it) and a real payload with its mandatory tail word removed (FINDINGS
  13.3's measured silent short decode). Section 10 closes C-6 in `datmove`,
  whose defect was correctly stated as *"no safe relocation verb exists for
  compressed rows"* rather than *"datmove corrupts archives today"*: the silent
  case is now a refusal naming the fix, `--compression 8 --expect` is the safe
  relocation verb, and a plaintext move with no keyword still succeeds as the
  control. The C-6 test itself is a measurement rather than a marker: retail's
  `0x01 0x02` at offset 2 MISSES six of eighteen `gwenc` outputs, every one a
  payload under 256 bytes, so `looks_compressed()` uses the byte as a prefilter
  and DECODES to decide -- measured 20 of 20 gwenc streams and 10 of 10 retail
  rows caught, 0 false positives in 6,005 synthetic plaintext samples, and both
  rates are re-measured by checks in the run rather than quoted from a
  docstring. **The false-refusal rate is NOT zero and the docstring names the
  rows**: 4 of 38,621 real stored rows in `dat_study` decode under our decoder
  (177242, 177264, 177332, 177333) although they do not re-emit like genuine
  comp-8 rows. Kept deliberately -- a false refusal is loud, writes nothing and
  costs one re-run with `expect=data`, while a miss is silent and costs the
  whole file and its nextStream chain permanently at the next repair (FINDINGS
  5.1). The trailer-agreement half of the test is honestly labelled as weak,
  because `gwdat` takes the declared size FROM the trailer and uses it as the
  decode loop's bound, so it can only refute a stream that runs out of input --
  and there is a check isolating exactly that, rather than a docstring claiming
  more. Re-emission was tried as a stronger confirmation and REJECTED on
  measurement: it reproduces retail's streams but 0 of 15 of our own. What
  none of it establishes: the round trip is through `gwdat`, which is OUR
  decoder, so it proves agreement and not correctness -- **A8, a caged client
  reading the row, is still the only oracle.**
  **Three defects found by the skeptic pass and fixed the same day, all one class
  — a guard that looked closed and was not.** (1) The C-6 arm was gated on
  `expect is None`, and `expect == data` is trivially true for ANY bytes, so
  `--data s.bin --compression 0 --expect s.bin` with genuine `gwenc` output wrote
  compressed bytes under a stored code through the documented CLI — exit 0,
  preflight 10 of 10, log line indistinguishable from an ordinary replace. The arm
  now consults the decode regardless of `expect`; the override is
  `--stored-lookalike-ok`, which announces itself. The old "hatch" control used
  bytes that do NOT decode, i.e. only the harmless half; `hatch_real` now covers
  the dangerous one. (2) `--overwrite` never reached `declaration_fault` and never
  touches the compression field, so overwriting a comp-8 row with same-length
  plaintext left a green archive whose `Archive.read()` returns **zero bytes**;
  it is guarded now. (3) The `toobig` case claimed to test the relocation refusal
  but `pattern()` compresses ~12x, so it fitted the reservation and was a second
  copy of the C-6 check wearing a false label — **the fourth recurrence in this
  arc of a check claiming more than the artifact does** (§10.6, §12.7, §13.6). It
  uses incompressible bytes now.
  **Sections 11 and 12 (2026-08-19) are the GROW-BACK VERB and the JOURNAL AS A
  DURABLE FILE, floor 138 -> 199.** `replace()` derived its ceiling from the
  row's CURRENT size, so after any shrink the row's own freed blocks were
  unreachable to it -- fatal for this arc's authoring loop, where the second,
  larger encoder output lands on a row the first write shrank (row 11196 on the
  real archive loses 1,025,536 B of its own space). `grow_to` is now a
  keyword-only argument the CALLER states; with it unset NOT ONE new check runs
  and every caller in the tree and the vault is on the old path, asserted. A
  greedy geometry-max default is REJECTED in the docstring, because `claimants()`
  computes each NEIGHBOUR's reservation from that neighbour's current size too,
  so geometry cannot tell a free block from a shrunk neighbour's wanted-back one.
  The gate is `Writer._grow_gate`, ONE copy shared with `--restore` (checked on
  the syntax tree), and it is four conditions where `restore()` had only the
  first: claimants; an EOF bound (`datcheck` rule 5 tests `offset + size`, not
  the rounded reservation, and `put()`'s short-read guard fires AFTER the
  decision); the live MFT, against the file header's own `mft_offset`/`mft_size`
  and NOT via row 3, which merely happens to describe the table on the copies we
  have measured; and `datplan.classify_runs`'s WITHHELD container runs, quoting
  `Exclusion.why()` -- the largest new risk in the verb, since `replace()` never
  needed to know about the rotation region because it never allocated.
  `--restore` gained all three by the factoring, which matters because it is the
  verb already run on real 4.2 GB copies. **Every arm gets its own fixture and
  its own SABOTAGE**, which is also the only way two of them can be reached on a
  4 KB archive: with `claimants` stubbed to `[]` the MFT arm still fires (so the
  protection is a check and not an accident of row 3), with `classify_runs`
  stubbed to "everything usable" the withheld grow is accepted, and on the
  claimed-blocks fixture the stub lets the write LAND -- which is the only way
  the post-write `datmove.overlaps` assertion can ever fire, and it does, naming
  both rows. The journal record for a grow covers the WHOLE NEW reservation and
  its `what` names the annexation with the range, so `--revert` restores the
  annexed region byte-for-byte (checked against 0xEE poked in beforehand, so the
  `before` field bites on real content rather than zeros). **Section 12 is the
  half nothing had ever tested: the journal as a FILE that has to survive the
  crash it exists for.** `flush()` opened `"w"` and re-serialised the whole
  document after every record with no fsync -- MEASURED 4.66x amplification on a
  5-record replace of this fixture, 5.0x on a 1,029,632 B reservation, and 34.1x
  / 533 MB on `a4run7-flip.journal`, 137x the archive bytes its 60 records
  protect, quadratic in record count -- and because `"w"` truncates first, a torn
  flush lost the WHOLE journal to an unhandled `JSONDecodeError` out of
  `revert()`: a traceback rather than a diagnosis, on the tool that exists for
  exactly that moment. It is now APPEND-ONLY, one record per line, fsynced per
  record, opened LAZILY so a refusal still leaves no journal behind. **The FORMAT
  did not move** -- the file is a valid JSON document at every fsync boundary,
  because 59 old journals under `vault/` and `test_datalloc.py`'s own prefix
  replay read it with a plain `json.load(fh)["edits"]`; what changed is that the
  header is written once, records are appended, and only the three-byte closer is
  rewritten. MEASURED 4.66x -> 1.00x, five truncating opens -> one, zero fsyncs
  -> one per record, each with a sabotage that drops it back. A journal cut
  through its last record replays every complete record and reports the dropped
  byte count; cut at 50% (mid first record) it is a NAMED refusal with nothing
  written; pure junk is refused without opening any archive. Old-format replay is
  checked against a journal SYNTHESISED in the temp directory -- this file never
  opens the vault, and that boundary is worth more than the realism -- and
  sabotaging the intact-document branch shows it is what keeps those 59 files
  readable, while the same sabotage over a NEW-format journal still reverts
  byte-for-byte from the line parser alone. **Section 11j closes FINDINGS gap D
  from the archive side**: `gwenc` now refuses to MAKE a zero-block stream, and
  `declaration_fault` refuses to WRITE one, naming retail's measured floor (the
  smallest comp-8 row is 56 B and holds a block). The artifact is exhibited and
  every OTHER arm shown to agree with it -- 12 B, prologue byte 0x02,
  decompresses without raising, trailer declares 0 against a 0-byte expectation
  -- which is why a new arm was needed; the comp-8-with-no-declared-payload
  refusal (hole 1) keeps its own separate reason, and the C-6 arm still sees the
  same bytes as compressed when they are declared STORED.
  **Section 13 (2026-08-20) gives the grow gate's refusal a TYPE, floor
  199 -> 212, and the defect it closes is in a CONSUMER.** `deploy.py` drives
  `--replace --grow-to` as a subprocess and may follow ONE kind of non-zero exit
  with a relocation -- the gate refusing, which is a fact about the archive --
  and must never follow any other, because a declaration fault turned into a
  quiet `datmove` is the failure. It told them apart by four fixed fragments of
  the sentences in `_grow_gate` ("is CLAIMED by", "PAST THE END", "LIVE MASTER
  FILE TABLE", "datplan WITHHOLDS"), so a reworded sentence would have turned
  every claimant conflict into a refused install -- silently, in the safe
  direction, for a reason with nothing to do with the archive. `_grow_gate` now
  raises `GrowGateRefused`, a `SystemExit` SUBCLASS carrying a `condition` from
  `GROW_GATE_CONDITIONS`, and `main()` prints one
  `GROW-GATE-REFUSED condition=<name>` line BESIDE the refusal -- never inside
  it, so every message is byte-for-byte what it was and §11a's verbatim
  first-sentence pin still holds, and the subclass means every existing
  `except SystemExit` in the tree and the vault is untouched. THE LOGIC DID NOT
  MOVE: four tests, same order, same sentences, same exit code. Each condition
  gets its own in-process fixture and is read by TYPE rather than by output --
  claimants and EOF directly, the live MFT and the withheld run behind §11's two
  stubs, which are the only way those two are reachable on a 4 KB archive.
  **The load-bearing checks are the two NEGATIVES**: a payload past the caller's
  own stated entitlement is an ordinary `SystemExit` and the CLI prints NO
  token, and neither does `--replace` with no `--data` -- a token on every
  failure would be worse than no token, and that is the shape a careless version
  of this change would have. Sabotage driven by hand, red: condition 1 put back
  to a bare `SystemExit` reddens 2. 212 checks against a floor of 212, was 199,
  was 138, was 136, was 87, was 78, was 66),

=== AMENDMENT 2 of 3 — test_deploy, section 10 and the floor (REWRITTEN for this fix pass) ===
  `toolkit/mapdata/test_datcheck.py` (the pre-flight and the detector, against a
  5.5 KB archive the test BUILDS -- never a real one, and no vault: every one of
  the ten open-time rules the client itself applies is broken on purpose and must
  go red ALONE.
  **§§8-11 added 2026-08-17, floor 84 -> 112, and three of the four exist because
  the ten rules above are BLIND to what they check.** §8, the MFT generation
  census: the client's repair does not rebuild a table, it hunts the file for a
  surviving older generation and adopts the highest flush counter, so "is a
  botched write recoverable" is a countable fact -- one generation REFUSES, a
  planted second one passes, and a candidate with `+0x08 != 0` fails the same
  shape gate ScanMft applies. §9, the payload CRC sweep, whose CONTROL is the
  section: a stale payload CRC passes ALL TEN open-time rules (10 of 10 clear)
  and then costs the entire `nextStream` chain the moment repair fires for an
  unrelated reason. §10, the file's own length: `snapshot` had recorded
  `size_on_disk` since it was written and `diff` never compared it, so an archive
  that GREW read as unchanged -- and the control asserts that appending past
  every extent changes NO MFT row, so nothing else could have caught it. §11, the
  header's `mftOffset` width: `archive.py` read `<I` while `datcheck` and
  `datwrite` read `<Q`, and the outlier was the one every tool imports. Proving a
  u64 read needs no 4 GB file -- set the high dword and require the failure to
  name the full offset, since a `<I` reader truncates, finds the MFT where it
  always was, and reports success. §8 is deliberately NOT a pre-flight item: it
  reads the whole file, and pre-flight costs 1.7 s precisely because it never
  reads a payload. **One of the ten was STRICTER THAN THE CLIENT and was corrected
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
  the same defect wearing the right name. Floor 75 -> 84. **§§12-12d added
  2026-08-20 with `assert_archive_safe`, the launch-side gate, floor 112 ->
  149.** This is the one part of the file that checks a REFUSAL rather than a
  verdict, because the two failure modes it stands in front of have no clean
  error between them and the archive: a header whose CRC does not verify
  tail-jumps `ArchiveOpen` into ArchiveCreate, which writes a fresh empty
  archive over 4.2 GB with nothing logged, and one stale payload CRC costs the
  whole `nextStream` chain the moment repair fires for an unrelated reason. The
  two rules the gate ADDS to the ten each carry the control that shows the
  pre-flight blind to them: an archive with a wrong MFT self-crc answers 10 of
  10 clear and is still rejected by the client's own LoadMft, and an archive
  whose row was rewritten LEGITIMATELY -- payload and crc agreeing, so every
  integrity rule is green -- is a different world that only the fingerprints can
  tell apart. The self-crc is compared against this file's own reading of the
  rule rather than against `datwrite.mft_self_crc`, so the two can differ.
  `deep=True` is pinned both ways (one generation refuses, the SAME archive
  clears without deep, a planted second generation clears it), the identity tier
  resolves a fingerprint DOCUMENT to its `rows` block and refuses one holding
  two UNNAMED blocks rather than guessing which side of a profile to match, and
  a full deep+fingerprinted run is proved to leave the file byte-identical by
  sha256 -- which is what the LIVE path rests on, since run-live's archive
  drifts on purpose and the gate may only read it. The three exit codes stay
  apart through the real CLI, so an unreadable archive is 2 and never 1. **§12d
  is the section the fix pass rewrote, and it is now about the CENSUS of launch
  sites rather than a list of them.** It asks FOUR syntax trees whether each
  calls the gate itself -- `session.run_client`, `drive_client.main`,
  `livesession.preflight`, `deploy.launch` -- and the fourth is the correction:
  the first revision named three and left out `drive_client.main`, the
  standalone operator launcher and the OTHER of the two doors session.py's own
  quoted comment is about (PLAN.md: "both launch sites (`drive_client.py`,
  `session.py`) assert it"), so the gate stood in three of four launch paths,
  which is the two-doors defect wearing the gate's own name. The list is
  therefore held against a census DERIVED FROM DISK -- every non-test harness
  file that hands an `exe` to `Popen` -- which reads {drive_client, livesession,
  session} and is refutable in both directions: it fails against the old
  three-site list and passes against the new four, so a fifth door cannot appear
  unlisted. The live site is checked for the ORDER of its call as well as its
  presence, with its own wrong-way-round control: a running client holds the
  archive EXCLUSIVELY, so a gate written above the client census answers a
  left-open live client "could not be read far enough to have findings" --
  unreadable damage, no action named, on ArenaNet's own 4.2 GB copy -- while the
  refusal written for exactly that case never runs. The same cause at the three
  sites with NO census gets the errno its own sentence instead
  (`LOCKED_REMEDY`), checked three ways: the remedy names the client on a
  PermissionError, does NOT name it on a parse failure, and end to end the gate
  names the lock exactly when the platform's own errno is the lock's. The
  negative control stays: deleting the one line from a COPY of deploy.py flips
  the check. MEASURED read-only over all EIGHT 4.2 GB archives in the vault:
  every one clears, 6.0-7.1 s, and re-confirmed at 6.2 s after the fix pass.
  Floor 112 -> 149. **S12e added the same day, floor 149 -> 168, after a seam
  probe ran the gate and `overlay --status` against the SAME documents and bytes
  and found them disagreeing five ways**: the identity tier compared by ROW
  NUMBER where every line of overlay is file-id addressed, so an archive the
  client had REARRANGED under the profile -- the exact state `--verify-after`
  exists to detect -- cleared the gate while overlay refused it; none of the
  document's three trust checks ran on the gate's side; five doctored shapes
  escaped as raw exceptions past every `except ArchiveUnsafe`, mislabelled at
  the CLI as an unreadable ARCHIVE; and a document with `rows` removed fell
  through to `retail_rows` and cleared a retail archive as "deployed". S12e
  closes each red-then-green: the identity tier resolves the document's
  `file_ids` through the archive's own raw table first (a document without them
  keeps row addressing and the receipt SAYS you are trusting row numbers),
  overlay-format documents pay overlay's own three refusals through a lazy
  import of overlay's own primitives -- with an EQUIVALENCE check feeding one
  document to both readers and requiring identical verdicts, controlled by
  neutering the verifier and watching four doctorings clear -- every document
  fault refuses as a fault of the DOCUMENT (exit 1, named), and the side of a
  profile is an explicit choice (`side=`/`--side`) that refuses ambiguity rather
  than resolving it by position. Floor 168),
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
  `toolkit/mapdata/test_propscan.py` (**what a donor's prop models ARE, measured
  offline -- the catalogue `deploy.py` never had.** WORLDMAPS-W24 served an
  authored place and the owner's second complaint was "the biome donor's model 0
  is a monumental building, not a tree -- 32 of them scattered like shrubs loom
  one-sided over the bowl": `deploy.py` wrote `prop_dep_ids =
  [donor.prop_model_ids[0]]` with every prop at `model=0`, so an authored map
  could place exactly ONE model, had no say in which, and nothing in the toolkit
  could say what it was. §§1-2 check the arithmetic against synthetic geometry
  with no archive -- bounding box, extent in 96-unit PLACEMENT CELLS (the
  actionable unit, because `pick_tree_cells` places on that grid), aspect ratio,
  and the report naming what it could not read rather than dropping it. The
  check worth reading is `fits_pitch` answering **None** for an unmeasurable
  model: "we could not read it" and "it fits" are different answers and only one
  is a licence to place 32 copies. §3 runs it against the real donor: Pre-Searing
  lists **229** models and all 229 decode, model 0 is **16.0 cells wide and 963
  tall** (W24's building, as a number), and model 77 -- which `area.ashcoil` now
  names -- fits the grid at 0.84 cells and is 7.6x taller than wide, both
  properties checked against the archive rather than against the content row's
  comment. **One check went RED on its first form and the correction is the
  entry**: it compared the ten most-placed models against "the ten least-placed"
  and concluded placement count carries no size signal, but 91 of the 229 are
  placed exactly once, so which ten is a TIE-BREAK -- one arbitrary slice gives
  mean 926, another 4163. Re-measured as a rank correlation over all 229 with no
  ties to break: rho **-0.219**, a weak signal, and the median of the twenty
  retail places ten-or-more times is still **7.3 cells** wide -- so choosing the
  most POPULAR model would not have avoided W24 either. Floor 11 = §§1-2, the
  mandatory core; §3 needs the study archive and declares a skip. A whole green
  run is 18, ~30 s),
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
  `toolkit/mapdata/test_refscan.py` (**what the tag-4 and tag-6 `value` words ARE**,
  `refscan.py`, over all 349 maps — 17 checks, floor 17). It closes
  `studies/customarea/FINDINGS.md`'s UNVERIFIED item 1 and the same sentence in
  `props.py`'s own header: *"The `value` u16 of tags 4 and 6 recurs across maps, so
  those are ids rather than per-map hashes — not measured."* **That reading is right
  for tag 4 and wrong for tag 6, and the argument it rested on could never have told
  them apart** — small indices collide across maps for the same reason small integers
  do, so "recurs across maps" is equally true of a local index and a global id. The
  BOUND separates them at once: tag 6's `value` is under `len(props)` on **10,647 of
  10,647** rows in 149 maps; tag 4's on **212 of 6,355**, with values to 65,521. A
  `PropRef` is `{u16 value, u16 prop}` and `props.py` documents only `prop` as an
  index — for tag 6 **both** words index the prop array (10,647 of 10,647 each), so
  the entry is a prop-to-prop relation. **THE 10,647 OF 10,647 IS NOT THE CHECK**, and
  that is the whole design of this file: an inequality over small numbers can hold by
  construction, so §2 asserts TIGHTNESS — `max(value)/(len(props)-1)` at a median of
  **0.939**, p75 0.981, **90 of 149 maps individually over 0.9** (a median can be
  carried by half a corpus, so that one is asserted separately), and **7 maps landing
  on `len(props)-1` exactly**, which a bound with slack in it would never do. §3 is
  the control that can embarrass the claim: re-score each map's values against a
  DIFFERENT map's prop count and **32.2%** fall out of range, so the ceiling is a fact
  about *this* map rather than about integers. It is asserted from **both** sides —
  a floor, because near-zero would make the whole reading vacuous, and a ceiling,
  because 100% would mean the prop counts share no scale and the control would prove
  less than it appears. §4 requires the two tags not to converge, since one decoder
  reads both from one file. §5 pins the **ten tag-6 self-references** (`value == prop`)
  against tag 4's zero — a 40-map sample had reported none, which is how a rare row
  vanishes, and any account of what the relation means has to survive them. **Stated
  limits, in the module header and not only here:** this does NOT show the indexed
  array is the prop array rather than another per-map array of equal length — bounds
  and saturation cannot separate those, only a consumer read can — and it says nothing
  about what the relation MEANS (parent, group leader, LOD substitute, sort key are
  all still open). Tag 4 is shown to be a wide cross-map namespace, not what it
  indexes; `studies/customarea` names the deps chunk / MFT as the join candidate and
  it is untested. Six deliberate breaks redden it, the load-bearing one being the
  shuffle control neutered to score against each map's own count. Archive only — no
  vault, no client, no run — and it declares one skip without an archive rather than
  passing on no data.
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
  9,128, ten values all <= 9, so it is an index. **Section 7 (added 2026-08-19)
  says WHICH index, and the answer is ArenaNet's own: `GR_FVF_GROUP`, the
  per-vertex skin group** (`MdlCombine:2073`, `GrGeo:738` -- two independent
  modules), resolved through `SubModel.trailing` into
  `groupTransformCount[u0]` + `transforms[u1]`. Every check carries the rival
  that must score worse, because the whole decode is arithmetic over small
  integers and that agrees with things by accident: **closure 1,285/1,285 with
  the reversed-order rival at 55** (`sum(groupTransformCount) == transformCount`
  is the client's OWN assert, `MdlCombine:860`, not a regularity we noticed);
  **surjectivity -- the group values are exactly {0..u0-1} -- 560/560 with the
  same field one dword later at 0/560**, and that tight form is the one that
  matters because the weak `max < u0` cannot separate this reading from a direct
  palette index; a **cross-structure oracle** (no sub-model declares more than
  one group without carrying the field to select between them) at 0 violations;
  and `GR_FVF_DIFFUSE` set on 0, which the client asserts it must be
  (`MdlCombine:2075`). **Skin weights are RULED OUT, not unestablished** -- the
  vertex holds no weight anywhere and the client's per-vertex loop takes exactly
  one matrix row, so per-vertex blending is refuted at the instruction level.
  A **sabotage** bumps one count by 1 and the closure refusal must fire, because
  a guard that cannot go red is a comment -- this arc has shipped five of those.
  The decode is what explains run 7's failed positive control
  (`studies/archivewrite/FINDINGS.md` 11.7b): **zero** vertices bind to the
  nodes that run scaled.
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
  (61 -> 64 with the H fixture, measured green before raising; **64 -> 70 with
  section 7's skin binding, 2026-08-19**). ~121 s),
  `toolkit/mapdata/test_modelwrite.py` (**the 0xFA0 GEOMETRY WRITER** -- the
  mesh half of the round trip and the LAST unwritten layer of a unit, added
  2026-08-19. Criterion is `skelwrite.py`'s: unmodified re-serialization
  **byte-identical**, because a writer that stashed the source block would pass
  every re-parse oracle while decoding nothing (`studies/models/FINDINGS.md`
  §4.5's memcpy-loader defect). **It could not honestly have been written a day
  earlier**: until FVF bit 1 was named `GR_FVF_GROUP` a writer had to carry four
  bytes per vertex as opaque, and with it named, MEASURED
  `stride - sum(named field sizes) == 0` on **1,618 of 1,618** sub-models across
  all **14** retail vertex formats -- no padding, no unclaimed byte, so the
  vertex block is RE-DERIVED field by field rather than copied. §4 is the
  control that makes identity mean something: it scales positions and requires
  the diff to land **only inside each vertex's position field**, which a memcpy
  writer fails; then it writes a changed `GR_FVF_GROUP` and reads it back.
  §1's synthetic fixtures (struct.pack, no ArenaNet bytes) cover what retail
  cannot -- the rigid no-binding case, collision meshes, an H/I/J tail, and a
  preamble whose sub-model count is WRONG and must be re-derived from the typed
  list rather than carried. The tail fixture found its own lesson: a tail
  without block J's gate (`u32@0x34`) set is not a tail but trailing garbage,
  and the client's closure at `0x007957CB` refuses the chunk. §5 provokes seven
  refusals by name, §2 pins both unit anchors (hatcher 116703, worm 116366) at
  chunk *and* whole-container level, §3 sweeps the corpus **250/250 across 12
  vertex formats** (`--all` for every row; the module's own CLI census took
  it to **6,846/6,846 archive-wide with 0 undecodable**, 2026-08-19). Floor **20**, and it was set the
  hard way: the first declared floor of 24 was a guess, the run executed 20, and
  the ledger refused it. ~24 s),
  `toolkit/mapdata/test_cpsdata.py` (**the COMPOSITE TABLE, Gw.dat `0x33EA` --
  where a PLAYER's file ids actually live**, added 2026-08-19 as rung U10's
  first module. `unitassembly.py` answers "which files does this MONSTER need";
  players are not on that path and had no answer at all. **The named suspect
  was wrong**: `ConstComposite`'s two 132-entry pointer tables in `Gw.exe` hold
  no file id at any depth -- they are texture-atlas RECTs, 359/359 satisfying
  `0<=l<r<=W, 0<=t<b<=H` where XYWH fails 269/359 and LRTB 284/359. The real
  table is an archive file, so the module reads `Gw.dat` and owes `Gw.exe`
  nothing. **The test exists mostly to attack its own decoder**, and it caught a
  real defect in the acceptance criterion it was written from: §2 first asserted
  that a wrong slot-mask width leaves a non-zero RESIDUE, and it does not --
  **every record consumes `4 + 4*popcount` bytes, so 9, 10, 11, 12 and 13 slots
  ALL close on the exact final byte.** That is a check that cannot fail, and it
  is now inverted into a check that the vacuity holds, next to the two
  discriminators that actually work: the record count must equal section 1's id
  count (3,803 == 3,803, against the rivals' 3,992 / 3,858 / 3,795 / 3,752)
  and cross-half type agreement must be total (3803/3803, against 3,212 /
  2,547 / 2,927 / 3,075 disagreements) -- the two halves are disjoint regions
  of the file, so agreement is two witnesses rather than one restated. The
  count equality is a REFUSAL in `decode`; the partition is only a method,
  because it is strictly stronger and §0 builds the fixture that separates them
  (two records, two ids, one used twice and one never). **§3 is the headline:
  the two-witness join.** Composite type 1 across every `(group, profession)`
  cell resolves to twenty file ids and an INDEPENDENT FFNA chunk walk must call
  all twenty composited (FA1 present, FA0 absent); type 2's twenty must then
  match type 1's node counts **element for element, 20/20**, on skeletons with
  10--115 sequences against type 1's 220--289. **§4 is what stops §3 being
  vacuous**: the hatcher 116228 IS composited and DOES walk, so a set-based
  check passes it as a player shell -- only the composite table can reject it,
  and 116228/116703/116377/116366 must all be absent from its 16,567 distinct
  file ids. Slot kinds are MEASURED from the archive ({0,5,10} `ffna`, 6,703
  refs; the other eight `ATEX`, 13,535; zero exceptions either way) rather than
  imported from the client's `s_fileFlags`. Mutation-tested: moving the sex
  slot or the type shift by one goes red, restoring goes green. Floor **58**,
  set from the green run -- nothing here can legitimately skip, so the floor IS
  the count. ~35 s),
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
  `toolkit/mapdata/test_playerassembly.py` (**the player-assembly rung — what
  sits ON the composite table**, `playerassembly.py` + the exe-side
  `clientscan/composite.py`. The composite TABLE itself — its decode closures,
  the geometry/texture split, the two-witness shell join, the monster-shell
  rejection — is `test_cpsdata.py`'s ground and is deliberately not
  re-litigated here. §1 pins the module's own sex/slot split as DISJOINT: sex 0
  reads {0..4,10}, sex 1 reads {5..9,10}, overlapping only at the shared slot,
  so a player's files are its sex's half and never the other's. §2 checks the
  manifest's record picks — the shell resolving to file 15018, all four base
  pieces, type 9 in by default and droppable, exactly one ROLE_SHELL seed, and
  texture vs geometry seeds disjoint. §3/§4 are the closure: group 0/prof 1/sex
  0 closes on shell **15018 — the archivewrite arc's hardest wall, resolved as
  a player identity** — in a pinned 173-file set, **all 40 resolvable
  identities close** and the 136 foreign-group cells REFUSE per the home-group
  rule. §5 re-checks the monster-shell rejection at the assembly boundary (the
  hatcher 116228 IS composited and DOES walk, so only the table can reject it).
  §6 pins the two capabilities the seeds split added: a ROLE_SOUND seed refuses
  outright (the audio closure hangs off a model's FA6) and a lone ROLE_TEXTURE
  seed CLOSES as a terminal (read, not walked as a model). §7 crosses witnesses
  with the exe extractor: s_fileFlags' clear bits equal the assembly's
  GEOMETRY_SLOTS from a disjoint source, base_types match the manifest's four,
  359 live rects LTRB-shut with 88 .data zero-fill records counted apart (the
  tail is MODELLED — a reader past a section's raw size returns zeros, not the
  next section's bytes), and the build is derived 38797 from the hash, never
  typed. §8 pins **`FILE_ID_RESERVED_BIT` = bit 31** (0x80000000, from
  CpsData:468/:484): every composite file id clears it (authoring is safe by
  construction), the raw file-id table DOES carry 25 reserved-bit ids mapping
  to MFT rows disjoint from the ordinary space (a real second namespace, not
  hypothetical), and `manifest` refuses a record carrying a reserved-bit id
  before it becomes a seed. Needs `vault/dat_study` (skips declared without it)
  and the pinned exe for §7; ~2 min; floor 34),
  `toolkit/mapdata/test_playerwrite.py` (**the player files round-trip through our
  writers BY NAME** — playercomposite §4.4's last blocker, answered with its premise
  corrected: "no player component file has ever been walked" was stale, because the
  U6/U8 sweeps ran archive-wide over flags=515 and every player file is a flags=515
  row — this test makes the JOIN and the named proof. §1 collects the 40 identities'
  closures into 180 distinct geometry files (40 shells, 140 components); §2 pins the
  population membership — all 180 flags=515 ffna rows, the 28-byte no-ffna anomaly
  row 8316 absent, shells FA1-with-no-FA0 (the composited⟺no-FA0 rule by name) and
  components FA0-with-no-FA1 (a player's only skeleton is the shell's); §3 is the
  named round trip — `skelwrite.rebuild_container` 40/40 and
  `modelwrite.rebuild_container` 140/140 byte-identical; §4 re-measures FINDINGS
  §1.22 through the writer-facing decoder (type-1 sequence counts span exactly
  220..289; type-2 is nineteen in 10..17 plus the single 115 outlier — reproduced,
  not remembered); §5 makes the identity informative on THESE files: the U7 seam
  retimes sequence 16 of shell 15018 itself (doubled keys read back from a fresh
  decode of the emitted bytes; the inexact-retime refusal proven ATOMIC — the
  representation still encodes the source), and `scale_positions` doubles 388
  vertices of component 8292 with the coordinates read back. What it deliberately
  does NOT claim: delivery — all 180 rows are compression-8, so shipping modified
  player geometry still waits on a compression-8 encoder or the client-compiler
  route. Needs `vault/dat_study`, skips whole without it; ~3 min (40 closure
  assemblies dominate); floor 15),
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
  blocks in, and that the plan names what it withheld instead of dropping it.
  **§9 added 2026-08-17, floor 38 -> 44: a mark is not the END of the generation
  it names.** Every check before it rested on where a signature SITS; none asked
  how far the table it declares REACHES. A generation whose extent runs off the
  end of its own free run leaves the next run with no magic at any boundary, so
  it scored usable and `best_fit` would place a payload inside a live table --
  measured on the 38833 study copy as a 2,892,800 B run lying 100.0% inside a
  stale generation's extent and accepted by `plan_move`. Four of §9's six checks
  are CONTROLS (runs past the extent still usable, the run before it untouched
  since a table is claimed forward only, the untouched fixture unchanged),
  because a projection that swallowed everything downstream would withhold the
  archive and protect nothing. It
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
  **Section 14 is the one a skeptic wrote.** Until 2026-08-20 this verb was the
  only writer of the three that committed a compression-8 payload with no
  declaration of what a reader must get back -- the string `declaration_fault`
  appeared in `datalloc.py` zero times -- and a `gwenc` stream with a corrupted
  trailer went to disk through `alloc(confirm=True)` and through
  `--stream FILE:1:8`, `Archive.read()` handing back 8,191 bytes instead of
  8,192 while `--verify`, preflight 10 of 10 and the overlap sweep were all
  green. The gate it had decides by DECODING, which refutes FRAMING damage and
  nothing else: `gwdat.decompress` takes the output size from the TRAILER and
  uses it as the decode loop's own bound, so over 528 single-byte flips of one
  real stream **132 were refused, 394 decoded to something else and were
  accepted, 2 still decoded to the payload**. `expect=` is now MANDATORY with
  `extraBytes 8` (`--expect FILE` from the CLI, one compressed stream per
  invocation), every stream is routed through `datwrite.declaration_fault` --
  which also brings the compression-0 direction, the stored lookalike section 13
  had recorded as an OPEN GAP, with the `stored_lookalike_ok` hatch its
  4-in-38,621 need -- and the gate runs in `alloc()` as well as `plan_alloc()`,
  because `alloc(plan=P)` ran neither and a doctored plan put `extraBytes 8`
  onto plainly stored bytes. **Twelve sabotages, all twelve red**, counts in the
  floor comment and re-measured after every change; the sharpest is
  `declaration_fault` stubbed to `None`, which reddens 12 checks and puts the
  corrupted stream back on disk in a green archive. ~~No client, though: **no
  client has ever read a row this verb allocated**, which is the same sentence
  `datmove` carried before FINDINGS 39.~~ **That sentence had its FINDINGS-39
  moment on 2026-08-20 — A9, archivewrite §18.6**: the retail client resolved,
  decompressed and animated from a 3-stream chain this verb allocated under a
  new file id, and the chain survived the client's Flush byte-intact. One chain
  shape, one build, one launch — the suite below is still what proves the verb
  in general. **Section 15 is the RESERVE** (2026-08-20, WORLDMAPS-W5), and its
  subject is a field that is deliberately not about the payload. Until this rung
  a created row's reservation was exactly `blocks_for(len(data))` -- zero
  headroom BY CONSTRUCTION -- so a created chain's second, larger install was
  already past a ceiling nobody had chosen and fell through
  `deploy.resolve_or_create` to a relocation; and the archive records no
  entitlement anywhere, the 24-byte MFT row having no such field, so the number
  has to be STATED by whoever authored the row. `Stream(reserve=N)` states it and
  reaches EXACTLY ONE line of the module -- the block computation in
  `plan_alloc`'s placement, `max(len(data), reserve)`. The whole risk is that
  it LEAKS, so every check asks the same question twice: that the RESERVATION
  moved and that the size, the crc and the declaration did NOT. A 900 B payload
  with `reserve=2560` is placed in 2,560 B of blocks against a CONTROL of the
  same bytes with no reserve taking 1,024 -- a different reservation AND a
  different run, since the fixture's usable runs are 1 block at 5, 2 at 7-8 and 6
  at 10-15 -- while `size` and `crc` are identical across the pair and the armed
  head still owns no extent. Three refusals, each with its own control: a reserve
  on a ZERO-LENGTH stream is refused naming the partner as the row that grows (an
  armed head has no offset to reserve blocks at, so a budget there would be
  accepted and do nothing), and the same empty head with no reserve still
  constructs; a reserve UNDER its own payload is refused rather than clamped,
  because `max()` would paper over it and report headroom nobody has, and a
  reserve exactly EQUAL to the payload is legal; and `1024.5`, `"1024"`, `None`,
  `True` and `-512` are each refused as not a whole number of bytes. A budget
  larger than the largest usable run is refused by the ordinary "nothing fits"
  placement rule -- a reserve buys real blocks or it buys nothing. The handed-in
  plan gets section 14's discipline in BOTH directions: a plan computed BEFORE
  the reserve was set would give the row what the payload needs while the caller
  went on believing it bought headroom, and a plan reserving blocks no stream
  asked for is the same disagreement from the other side; both are refused with
  the archive byte-identical, because `r.reservation` is carried out verbatim and
  can never be re-derived afterwards. Finally the WRITE, judged on bytes rather
  than on the planner's word: the row declares the payload's size and crc, holds
  exactly the bytes handed in, and is ZEROED across the whole budget -- the
  fixture fills unclaimed space with 0xCC, so 1,660 bytes of zeroes past a 900 B
  payload is the reservation being real rather than the padding a 2-block row
  would have had -- with `datcheck --preflight` 10 of 10 and no two rows sharing
  storage. Floor 203),
  `toolkit/mapdata/test_authorflow.py` (AUTHOR A FILE THAT NEVER EXISTED INTO
  AN ARCHIVE, AT COMPRESSION 8, AND WALK IT BACK. Every verb here has its own
  test and all of them are green; what none of them measures is the SEQUENCE,
  and this arc's history is composition defects -- `replace()` could not grow a
  row it had shrunk itself (FINDINGS 14.4), and `datmove` marked a relocated
  compression-8 row stored (C-6) -- both green in isolation on the day. Six
  steps over ONE archive, `test_datalloc.py`'s 28-block fixture in a temp
  directory: AUTHOR four revisions through `gwenc.encode` (one of them RLE, the
  shape that declared a 1-symbol distance table until the envelope work landed,
  gap A); CREATE via `datalloc.alloc(confirm=True)` with a partner declaring
  `extraBytes 8` **and the payload a reader must get back**; REVISE smaller in
  place through the real command line, which frees the second block; GROW back
  into it with `--grow-to`, the step that was impossible before 2026-08-19 and
  the one an authoring loop hits on its second iteration; OUTGROW, where
  `--replace` refuses and picks its remedy sentence FROM THE GEOMETRY -- step 4
  gets the `--grow-to` branch and step 5 gets the other, which makes the pair a
  measurement of the choice rather than of one message -- and
  `datmove.move(compression=8, expect=)` relocates; UNDO, four journals
  replayed newest first, composing back to the pristine fixture BYTE FOR BYTE
  with every intermediate state checked too, because a chain that only agreed
  at the ends could be two errors cancelling. **Every step is checked by
  DECODE, never by a checksum**: the entry crc covers the STORED bytes, so it
  moves with the corruption and no checksum in this format can tell a
  compression-8 row holding the wrong bytes from one holding the right ones.
  **The sabotage in step 2b is what stops this being a demonstration that the
  tools ran** -- if every gate were stubbed the six steps would still print six
  greens, because an archive faithfully hands back whatever the last write put
  in it. It corrupts the authored stream three ways, and as of 2026-08-20 it
  takes TWO gates to catch them: a flip inside the Huffman table breaks the
  framing and `looks_compressed` sees it; a corrupted TRAILER does not break
  the framing at all, decodes one byte short and agrees with itself about it,
  so only the decompress-and-compare against `expect=` can see it; and a
  missing declaration is refused outright. MEASURED: `looks_compressed` stubbed
  alone leaves 1 red, `declaration_fault` stubbed alone leaves 3, both together
  leave 4 **and the corrupted stream reaches disk**. Six sabotages in all,
  counts in the floor comment. Floor 59),
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
  **29 install / 9 run-live** exactly, and the STUDY census as one of two KNOWN
  STATES -- **25 on a 38797-lineage copy, ZERO on 38833/38849**, because ArenaNet
  dropped the dual registration between those builds and `vault/dat_study` was
  resynced across it (`studies/maprows` sec.10.14). The asymmetry is deliberate:
  `client/` and `run-live/` are dated snapshots that are never resynced, so a
  move THERE is a real regression and must stay exact, while the study copy's
  number is a per-generation fact. The install->study claim splits with it -- on
  a 38797 copy it still clears exactly 4 ids over TWO rows with NEITHER a map
  row (corroborating `customarea/FINDINGS.md`:967's correction of "two map rows"
  to **four** from an archive that file never read), and on 38833 the assertion
  worth making is the opposite one: the disappearance is TOTAL and clean, taking
  the map rows with it, because a PARTIAL clearing would be a third state. The
  two arms assert genuinely different propositions and must not be collapsed
  into one parameterised check. Floor 85, plus one on a copy that still
  registers, so neither generation carries slack.
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
  `toolkit/mapdata/test_gwentropy.py` (rung **A6**, the entropy accountant --
  `gwentropy.py` recovers RETAIL'S OWN token stream out of a compression-8 row and
  re-costs it under a from-scratch Huffman plus this format's meta-coder, so the
  standing hazard is that our decoder is the only referee and a round trip through it
  proves nothing. Every section is picked for what a RED would mean. **C1** is the
  one that earns the file: the segment accounting -- header + both tables + block_size
  fields + tokens + extra bits -- must equal the MEASURED final bit position, with the
  token term MODELLED from reconstructed length x count rather than read off
  `bit_end - bit_after_size`, which is the version that could not fail and is
  deliberately not what this does. It closes to **0 bits on 11 of 11 rows**. **C1b** is
  the reader identity `bitpos + 32 + avail == 8*idx` with `idx == len(data) - 4` --
  written as an identity because "within one 32-bit word" is FALSE as literally stated
  (the reader permanently holds 32 look-ahead bits it never consumes; real tail slack
  is 33..63). **C1c** asserts the derived `bitpos` equals an independently accumulated
  counter, so `bitpos` is a measurement and not a definition. **C2** is why duplicating
  gwdat's block loop is affordable: `trace()` and `replay()` must each reproduce
  `gwdat.decompress`'s bytes, the second from the recorded token arrays ALONE with no
  Huffman table and no bit reader. **C5 is the check nothing of ours forces** -- retail's
  own decoded code lengths go back through our meta-coder DP and the answer is compared
  to the table bits measured off the bit reader, and `above > 0` (the DP costing MORE
  than retail's real bits) is impossible unless our cost model is wrong, since the DP is
  the minimum over the same alphabet. It gets **4,450 chances in section 5** and fires
  zero times; SABOTAGED by shaving one bit off one of the 256 meta tokens it goes red in
  both directions (2 tables `below`, and 2 `above` with the bit added). **C4** exists
  because C3 cannot substitute for it: swapping two symbols' code lengths leaves Kraft
  at exactly 0 and moves C1 by 3,528 bits, and only C4 -- which rebuilds all 256 nodes,
  24 `trans` rows and every `vals` entry from the reconstructed lengths and diffs them
  against what `build_table` produced -- names the node. **FRM** is the bits-to-bytes
  bridge (`4*ceil((bits+32)/32) + 4`) and this entry used to call it a prediction of the
  MFT's own `size` field, "a field that is not an input to the calculation". **That was
  wrong and the skeptic pass caught it**: `ar.raw(e)` slices the payload to `e.size`, so
  `len(data) == e.size` by construction, C1b already pins `idx == len(data) - 4`, and the
  algebra forces agreement for every stored size divisible by 4 -- which is **138,708 of
  138,708 comp-8 rows**. FRM cannot fail anywhere in the population it runs over; it is
  C1b in other units, kept as bookkeeping and no longer counted as evidence. Note also
  that **C5's independence is narrower than "nothing of ours forces it"**: it is genuinely
  independent of `table_lengths` and of the DP's run logic, but the DP and `build_table`'s
  measured consumption are both driven by the same borrowed `CODE_LENGTH_THRESHOLDS` /
  `CODE_LENGTH_SYMBOLS`, so a shared error in THOSE is invisible to it -- the standing
  `gwdat.py` risk that the xentax.cpp diff has never been run. Section 1 pushes
  all **65,536** 16-bit prefixes through `build_table`'s own band-selection expression
  and requires our inverted cost table to agree; section 3 brute-forces every complete
  length assignment for small alphabets, which is what makes "our token bits tie
  retail's" a result rather than an artifact of reusing their numbers. There is
  deliberately **no authored bitstream** here -- that needs a packer, and A6 is a
  bit-COUNTING rung. Floor 91 with ZERO headroom, measured green; `--stride` moves how
  many rows section 5 sweeps and not how many checks run. Without the archive it skips
  to 13 and goes RED, which is the intended verdict. ~41 s),
  `toolkit/mapdata/test_gwmatch.py` (rung **A7a**, the LZ77 matcher — `gwmatch.py`
  reports a byte figure for a token stream **nobody ever emitted**, and every cheap way
  to make that figure look good is a stream that could not be decoded: a distance one
  past the window, a match reaching back further than the bytes produced so far, an
  overlapping copy the encoder and decoder disagree about. All three make the file
  SMALLER. So the two sections that carry this file are the ones that make a small
  number mean something. **R1, reconstruction:** `gwentropy.replay()` rebuilds the
  payload from our token arrays ALONE — gwdat's own `LENGTH_BASE`/`DISTANCE_BASE`,
  gwdat's own one-byte-at-a-time copy loop so overlapping matches behave exactly as the
  decoder makes them behave, no Huffman table and no bit reader anywhere — and it must
  be byte-for-byte equal on **every real row and every synthetic**. That is why A7a
  needs no bitstream writer to be believed. **R2, decodability:** `validate()`
  re-derives each constraint from `gwdat.decompress`'s own arms rather than from the
  emit path. **And the SABOTAGE section keeps both honest** — six corruptions of a real
  token stream, each asserted CAUGHT, with an uncorrupted control beside them so the
  reddening is the sabotage and not the fixture: (a) a distance off by one *chosen to
  stay entirely legal*, where **R2 sees nothing and R1 is the only thing standing
  there** — the single sharpest argument for why a size-only rung still needs a
  reconstruction; (b) a match one byte longer than it is, where every per-token arm of
  R2 stays silent and only R1 plus R2's global byte count fire; (c) a distance past the
  bytes produced, which is what `gwdat` RAISES on; (d) distance symbol 30, off the end
  of the real `DISTANCE_BASE` and into the garbage the 46-entry table holds; (e) a
  non-final block that does not fill its declared size, which silently decodes the next
  block's tokens through this block's tables; (f) a length extra one bit wider than its
  own field. Section 1 derives every format parameter from `gwdat`'s tables rather than
  typing it and checks **all 32,768 window positions and all 256 length bases**
  round-trip, with the load-bearing arm being that **no distance ever reaches a symbol
  above 29**. Section 2 is the degenerate controls where the answer is known by hand:
  all-zeros is exactly `1 + ceil((n−1)/258)` tokens and every match is distance 1 (an
  overlapping copy), a 2-byte cycle is `2 + ceil((n−2)/258)`, and an incompressible
  payload may not come out smaller than itself. **Section 4's load-bearing check is not
  a size at all** — it is that **no uniform partition beats the partition DP**, measured
  over all 16, which is impossible unless the DP is wrong since the DP is the minimum
  over that same space; same shape as `test_gwentropy.py`'s C5, and it is the check that
  earns A7a's headline, because the partition is where the result came from. Also per
  row: C1 (the segment accounting re-summed by `gwentropy.segment_bits` must equal the
  cursor `build_stream` accumulated — a partition bug desynchronises them, so it is worth
  keeping, **but on OUR stream it is BOOKKEEPING, not evidence, and cannot fail**: both
  sides derive from the same `token_bits` formula, unlike on retail's stream where the
  token term is modelled and the final position is measured. **This is the second time in
  two rungs that a forced check was written up as a refutable one** — see `FRM` in
  `test_gwentropy.py` above — and it is why CLAUDE.md's "a check that cannot fail is not a
  check" is worth re-reading before writing the verdict line, not after) and the Huffman
  bracket (token bits at or above the per-block Shannon entropy and within one bit per
  symbol of it, a theorem rather than a property of our code). There is deliberately
  **no bitstream and no round trip through `gwdat.decompress`** — A7a is size-only.
  Floor 62 with ZERO headroom, measured green; `--rows` moves section 4's check count,
  so shortening it reddens the run on purpose, and without the archive it drops to 34
  and goes RED. ~28 s),
  `toolkit/mapdata/test_gwenc.py` (rung **A7b**, the bitstream writer — `gwenc.py` is
  the first thing in this arc that emits bits, and the whole point of the file is that
  its three checks are **not equally strong**, because `gwdat.py` is OUR decoder and its
  own docstring (`gwdat.py:81-84`) says the diff against `xentax.cpp` has never been run.
  **B1, byte-identical re-emission of retail's own rows** (§5, §7) is the only check in
  the rung that does not assume `gwdat` is correct: trace a stored row, re-emit from what
  the trace recorded, require the bytes to equal the row on disk **and `crc32` to equal
  the MFT's own recorded value**. A wrong bit order, a wrong canonical assignment, wrong
  extra-bit widths or a wrong meta-token encoding cannot accidentally reproduce
  ArenaNet's bytes. Its population is drawn by a **stated reproducible rule** — every
  comp-8 row of the archive bucketed into five stored-size bands, sampled with
  `random.Random(20260818)`, plus the anchors, `gwentropy.WITNESS`, and the four rows
  carrying the divergent zero-length distance table — and failures are reported **by
  class**, because a systematic class is a finding about the format while a scatter is a
  bug in the writer. **The scope limit travels with it**: B1 validates the BIT layer and
  not the SEMANTIC tables, since `LENGTH_BASE` / `DISTANCE_BASE` / the
  `first_four + base + 1` arithmetic are replayed verbatim from the trace — a wrong one
  of those gives a wrong payload and a *bit-identical* stream. **B2, the round trip**
  (§3, §7) is `gwdat.decompress(encode(p)) == p` over real rows and fourteen adversarial
  synthetics (one byte, all-zeros, all-0xFF, incompressible noise, run-length and short
  cycles, a match at **exactly** the 32,768 window edge with a check that the edge is
  genuinely REACHED rather than merely survived, and two `uniform=1`/`uniform=2`
  partitions so the "a non-final block holds exactly its declared token count" rule is
  exercised a dozen times) — and it proves **agreement with our own decoder, not
  correctness**. The fifteenth fixture is gone and is now a **refusal check**:
  `encode(b"")` RAISES as of 2026-08-19, because a zero-block stream (12 B of prologue
  and epilogue) is a shape no retail comp-8 row has — the smallest is 56 B and holds a
  block — and `datwrite.declaration_fault` accepts those bytes today, since its
  zero-length guard tests the STORED bytes rather than the payload. That is FINDINGS
  §13.5's gap D, closed at the encoder. **B3, the size closure** (§4) compares the
  writer's ACTUAL emitted bit count against `gwmatch`/`gwentropy`'s PREDICTED one — in
  **bits**, because the byte figure is a 32-bit-quantised view and a writer 31 bits off
  the model still lands on the same stored size. **And B3 has been WATCHED FIRE**, which
  took finding the right row: `gwmatch` plans its tables with the meta DP and a writer
  hardcoding retail's greedy emits more bits than the planner charged, but on *most*
  streams the two agree exactly — 0 bits apart across row 11196's own 218 tables — so a
  randomly chosen row demonstrates nothing. Row **73015** is pinned because there the
  wrong flag costs **+9 bits**, and the resulting stream **still decodes perfectly**, so
  B3's comparison is the only thing in the file that sees it. §2 is the arm FINDINGS
  §12.6 says A7a never had: **984** tables our encoder implies, serialized and rebuilt by
  **`gwdat.build_table` itself** rather than by a model of it, with the decoded lengths
  diffed against the intended ones — and it now runs **both** table builders, because
  they are different functions with different jobs: `gwentropy.table_for_counts` is the
  MODEL path (`recost`, `literal_only`) and `gwentropy.authoring_table` is the WRITER
  path, and it is the writer's tables that would reach an archive. **§8, the envelope, is
  new (2026-08-19)** and it is what keeps that split honest: every table the encoder
  emits over the whole synthetic corpus must be a SHAPE retail's own archive or the A8
  client run attests — declared ≥ 2, distance declared ≥ 5 (the minimum over 32,831
  comp-8 rows ≤ 2,048 B), literal declared ≥ 257 (the minimum of the 218 tables in the
  row the retail client READ, §16.2 — **not** 258, which would have changed that row's
  bytes), no zero-length LITERAL table (0 of those 32,831 rows has one), and a
  zero-length DISTANCE table only ever in the all-skip shape `{declared-1: 0}` that
  `gwdat.py:265-267`'s `total == 0` fallback can actually install. That closes FINDINGS
  §13.5's gaps A, B and the distance half of C; **E is accepted rather than fixed** and
  `gwenc.py`'s docstring carries the reason (the meta bands tile structurally, so
  avoiding the catch-all-band indices would distort the partition DP's own costs for no
  attested benefit). §8 has **two** sabotage arms and they prove different things: five
  planted faults, one per rule, each of which must be NAMED while a clean block must not
  be — that proves the CHECKER can fail; and the pre-envelope builder restored in memory
  for one fixture, which must turn the sweep RED (on `b"A"` it names a distance table
  declared 1, a literal table declared 66 and that literal table being zero-length) —
  that proves the sweep is WIRED to the encoder and not only to itself. §7 pins the
  anchor twice over: the emitted size is A7a's modelled **1,011,244 B** to the byte, and
  since 2026-08-19 the **crc32 of our own encoding, `0xd03ab671`**, is pinned as well,
  because §16.1's result is about BYTES — the retail client read exactly those, so an
  encoder change that holds the size while moving a bit has lost the only oracle result
  the arc has. (The envelope work was landed against that number and did not move it: the
  anchor's tables declare literal 257–285 and distance 24–30, all already inside the
  floors.) §6 is the breakage set, and **(c) is the one that matters** — flipping the
  meta plan from retail's longest-run greedy to our optimal DP on row 150875 produces a
  **valid, smaller, DIFFERENT** stream, which is what makes A6's "retail's table encoder
  is greedy" load-bearing here rather than decorative. §6(d) records the format's most
  dangerous property for a writer, in two halves: dropping the `0x80010008` look-ahead
  word **entirely** still decodes (the u32 trailer slides into the slot, so `gwdat` does
  not need the sentinel at all), and one word shorter again **truncates SILENTLY** — no
  raise, no short-read signal, and the row still passes every checksum rule because the
  MFT crc is over the stored bytes. **Deliberately NOT listed as evidence:**
  `len(out) == framing_bytes(consumed)` is asserted inside `gwenc.finish`, which computes
  the length from that very formula — it cannot fail, and the refutable form is §4's.
  There is deliberately **no `datwrite` verb and no archive is opened for writing**; A7b
  produces bytes in memory. Floor **60** with ZERO headroom, measured green 2026-08-19
  (was 55: §8 adds 4, §7's crc pin adds 1, and §3 held its count because the deleted
  `empty` fixture became the refusal check that replaced it); `--per-band` / `--quick`
  move how many ROWS §5 re-emits and not how many checks run, so the row count is itself
  the last check of §5 and `--quick` reddens it on purpose. Without the archive it drops
  to 32 and goes **RED** — the same verdict its two siblings give, and for the same
  reason: B1 never ran. ~110 s),
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
  same worktree. Section 11 (2026-08-26, ROUTER-B4) covers `route()`'s
plane preference and `with_planes` corridor planes: twenty routed pairs
prove the aux planes are a decoration (identical paths), the endpoint
planes belong to trapezoids actually containing the points, a REAL
stacked point on Pre-Searing ((-6854,13008), planes {0,36}) has each of
its surfaces selectable by preference, and an unmatchable preference
falls back rather than refusing — the run-2 twelve-waypoint island tour
was blind `containing()[0]` endpoint selection, and this section is its
regression. Section 12 (ROUTER-B5): `nearest_walkable` returns an
on-mesh point at distance zero for an on-mesh query, leads a real ≤12u
edge penetration back to a verified-walkable point no farther than the
step off, and returns None in the middle of nowhere — run 3's
218-second refusal lock-in stood on an 8u penetration this query now
answers. **§12d and §12e were added 2026-08-29 because the DISTANCE was
wrong** (FINDINGS §1z-l): the query clamped y into the trapezoid's span
then x into its edges *at that y*, which is the true nearest only when
that edge is axis-aligned — against a slanted edge it walks along y then
along x instead of projecting perpendicularly. The docstring's "error
bounded by the edge slope over the radius" held for the radius-16 origin
rescue it was written for and **quietly stopped holding when
`noclipscore.py` asked at radius 600 and published the answer as "how far
off-mesh"**; measured against dense boundary sampling it over-reported by
up to **2.967×** (77.43u where the truth is 26.10u) and 64.91u absolute,
now 1.000× and 0.00u. §12d pins the geometry on a **synthetic 45°
trapezoid**, because a real mesh cannot isolate the property, and carries
the control that decides whether the check means anything: the OLD
arithmetic must still read 50.000u on that same fixture, 1.41× the exact
35.355u. §12e pins that the returned distance describes the returned
point — the boundary nudge used to move the point *after* the distance
was taken — over 596 real probes; **its first draft found ONE probe and
would have passed vacuously**, because these trapezoids are hundreds of
units wide and a fixed step off the centre never leaves them, so the
probe is now derived from each trapezoid's own edge. Floor 75 → 80. Section 13 (2026-08-28, MOVECODE R5) is the CORNER PULL, and
it is the section a reader should copy the shape of: `_shared_edge`
answered the MIDPOINT of the interval two trapezoids share, so a body
standing near one end of a long shared edge was routed to the middle of
it first — on map 280, trapezoid 531 borders corridor 1921 along
x∈[448,3936] and a player at x=3367, 43 units from stepping straight
north, was sent **1,176 units WEST**; 7 of R5's 34 routed clicks granted
a first leg pointing away from the click (cos to −0.92, detours to
1.50×), and the operator reported it before any instrument saw it. The
**MOVECODE-1z-ch (2026-09-07) changed the pass this section pins:** the crossings are seeded on the straight line origin→goal and the pass runs to convergence (64 rounds cap), portal crossings slide within the overlap region (`_overlap_rows`), and the unshortened pulled path is a lazy third candidate; the monotonicity control below read 30 of 119 LONGER on the first draft (the pulled candidate returned without the midpoint comparison) and 0 after, and §14's 50 ms tick bar read 84 ms with the third candidate gated unconditionally and 35 ms lazy. The CONTROL is what makes the rest evidence: with `CORNER_PULL_ROUNDS = 0`
the specimen must STILL route backward (cos < −0.5) — a fix whose
control cannot reproduce the bug is asserted, not tested. Then the fix
(first-leg cos +0.85), no length paid (4,711u against 7,930u), every
segment re-clipped, and the two no-loss properties over a 120-draw
sweep with an exposure guard so a sweep that routed nothing cannot pass
them vacuously: **0 of 119 paths lost, 0 longer**. Both were REAL reds
first — the first minimiser was wrong for same-side neighbours and made
19 of 300 corpus paths longer, and pulled points can cut a corner the
midpoints rounded off, which lost 4 of 300 until route() started scoring
the midpoint answer as a fallback CANDIDATE rather than replacing it.
**Section 14 (2026-09-04, MOVECODE-1z-bb) is the SEAM-AWARE PULL AND GATE**,
and it exists because RUN-1zBA measured the plane-blind one on a router
grant: the drawn body parked at a bridge deck's edge for 7 s while the
server's copy walked 2 km, then a 2,021 u teleport. `planes_at` (the grid's
plane set) is put against `containing()` over a lattice; `seam_clip` on a
five-trapezoid synthetic bridge — a deck over ground at its south end, the
file's own zero-height portal LINE pair at the deck's south edge, ground
south of the line, an east bank the deck's side abuts with no portal — stops
at the deck's side where plain `clip()` walks onto the bank (the specimen in
miniature), reads the seam DIRECTIONALLY (plane 0 ends under the deck's edge;
plane 1 continues over the same ground), passes through the line portal and
stops at it when the link is removed (the primitive's known-bad arm), and
treats an in-plane step across the line trapezoid as no seam. `route()` from
under the deck onto it U-turns through the portal (3 waypoints) with the term
on and is the straight line through the deck's underside with
`SEAM_AWARE_ROUTE = False` — the defect reproduced on demand; a goal in
another component is None in both arms; `planes=None` is the old pull
unchanged. On Pre-Searing (skip-declared if absent): RUN-1zBA run 4's grant —
`seam_clip` on plane 18 from (10989, 5236) toward the off-mesh click stops at
the deck's west edge (x = 10860 ± 12) where `clip()` runs 2,159 u; over 300
chase-band pairs the None counts are equal, every changed path but a handful
had a blind crossing before (measured 4 changed, 3 explained), no seam-aware
route crosses a blind seam by a `containing()`-based walker (a second point
test, not the grid the pull used), and route() stays under the 50 ms tick
(max 34.8 vs 25.1 ms plane-blind; p50 0.95 vs 0.56). **Section 10's
"nothing changed an answer" control now runs with the seam term OFF**: it
is the 2026-08-13 performance fix's control, and with the term on it read
12 of 1,500 paths changed and Nones 48 → 38, which was the seam term working,
not the fix regressing — section 14 owns that census.
**Section 16 (MOVECODE-1z-ce, 2026-09-06) is `wall_slide()`**, the rule ArenaNet's
server follows when a keyboard report's heading ray is blocked at the body: the NEXT
VERTEX of the wall the body presses against, in the heading's slide direction. Pinned
on a lone square (the slide both ways, a head-on press that slides nowhere, a heading
away from the wall, a horizontal wall, the corner, the chord cap, the lazy index) and
on Pre-Searing's stairs -- RUN-GROUNDZ-R3's report (10444.9, 8356.0) plane 29 heading
due east lands on the stairs' side vertex (10671.37, 8577), 316 u at 44.3 deg, where
the shipped lead was 0 u; 4 u short of that vertex the answer is still that vertex
(the decomposition's split points count, because retail's do); the next side's vertex
after it. The live-corpus derivation is `studies/movecode/review/wallslide.py --check`.
Floor 116 against a green 120 on 38833 (the archive-conditional §6 checks, §13
when map 280 is absent, and §14(g)/§16(l-p) when Pre-Searing is absent skip-declare);
~110 s, `--routes` shrinks section 10),
  `toolkit/mapdata/test_spawncheck.py` (the map-row spawn census, `spawncheck.py`,
  which answers a clause `PLAN.md` §3.2 had carried unmeasured since it was written:
  *"how many of the nine pass the trapezoid test has not been re-run, so the map figure
  is a row count and not yet a score against this criterion."* It is fifteen rows now and
  the score is **8**. `test_pathmap.py` §4 checks ONE spawn -- Kamadan's, hardcoded --
  so nothing walked the content store until this. The verdict is five-valued because each
  failure has a different cause and one number hides which: PASS, SEAM, OFF-MESH,
  WRONG-PLANE, UNRESOLVED. **The SEAM token is the finding.** `content/maps.toml`'s
  header says "EXACTLY ONE is what a non-overlapping tiling gives", and that sentence has
  a boundary case it does not mention: `Trapezoid.contains` closes BOTH y bounds, so a
  point on the horizontal seam between two vertically adjacent trapezoids is in both.
  Maps 143 and 144 sit exactly there -- authored `(1536, 1536)`, and 1536.0 is precisely
  where one trapezoid ends and the next begins. Walkable ground, a pass, and a different
  thing from an overlap. §3 SABOTAGES that reading rather than asserting it: it
  re-implements `contains` with a half-open y interval and requires the same points to
  collapse to one, with an interior PASS row as the control on the control (the sabotage
  must move nothing else, and moves 0 of 6). **THE MUTATION CAMPAIGN IS THE REASON THIS
  FILE IS THE SHAPE IT IS.** Seven breaks were built on 2026-08-27; the first pass caught
  three, and every escape was a real defect rather than a missing assertion. (1)
  `_share_an_edge` forced to `return True` survived, because §4 was calling `spawncheck`'s
  own predicate and asserting the mutant against itself -- it computes the shared-edge set
  inline now. (2) Chasing WHY that predicate did no work found that it tested only the
  y axis, so a **VERTICAL seam** -- two trapezoids in one y band meeting along a shared x
  boundary, which `contains` also closes -- was being filed as OVERLAP. That is walkable
  ground condemned, and the fix is in `spawncheck.py`, not in the test. (3) Collapsing the
  overlap branch into an unconditional `SEAM` survived, because **no content row overlaps**
  and the branch is unreachable from real data. §4b is the positive control that answers
  all three: four synthetic meshes, each isolating one term. A wide overlap must score
  OVERLAP; an edge-touching pair must score SEAM; a vertical seam must score SEAM; and a
  **sub-eps sliver** -- two trapezoids overlapping by less than `SEAM_EPS`, so every
  diagonal nudge escapes it and the interior probe reads a clean 1 -- must still score
  OVERLAP, which only the edge test can do. The mirror of that case earns the other term:
  a **seam-touching overlap** (three trapezoids meeting at one y, two stacked and a third
  straddling the line) is on a genuine shared edge, so only the interior probe can see it
  is also an overlap. Both terms are now provably load-bearing in both directions, and the
  campaign closes **7 of 7**. §5 pins the **(0,0) accident**: five rows carry a placeholder
  arrival point, four fail honestly, and Sparkfly Swamp's lands on walkable ground and
  scores a clean PASS -- a placeholder that passes is worse than one that fails, because
  it looks verified, so the count is asserted. §6 requires no row to score OVERLAP, and
  requires every UNRESOLVED file id to resolve in SOME vault archive -- "not in the
  archive" and "not in THIS archive" are different findings, and `--find-missing` keeps
  them apart: the three created chains (165/166/167) resolve in exactly one place,
  `run/2026-07-29_…-probe`, a 38797-era probe directory and none of the current run dirs.
  The TOTALS are deliberately NOT pinned -- `PASS=6` would redden on every new map row and
  train the reader to re-baseline instead of look; named rows keep their verdicts, the set
  keeps its invariants, the arithmetic moves freely. Floor **44** against a green 44, and
  the first draft declared 36 against a body that could only produce 33 and was correctly
  called incomplete. ~25 s),
  `toolkit/mapdata/test_deploy.py` (rung G's one command, `deploy.py`, which
  takes an area row in `content/areas.toml` from geometry to a map the retail
  client compiles. It is an ORCHESTRATOR -- nearly every line it runs belongs to
  a module with its own test -- so this file checks only what is true of the
  COMPOSITION, and each of its sections is either a defect the first runs of the
  command actually had or, for sections 4-9, a claim about the bytes the row
  will hold. **The two kinds of borrowing are different**: structural
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
  exact sabotage and requires the answer to flip. **The row holds COMPRESSED
  bytes now, and the fit is judged on those** (2026-08-20, WORLDMAPS-W1):
  `install_bytes` runs `gwenc.encode` after `assemble` and prints both sizes and
  the ratio every run, and `install_partner` threads `--compression 8 --expect
  <plain>` through BOTH writers -- `datwrite --replace` and `datmove --move` --
  because compression only RAISES the ceiling and a compressed replace beside a
  stored relocate would put the deviation back exactly where a bigger map lands.
  Section 7 runs five real installs against a hand-laid archive holding one map
  chain whose reservation the FILE chooses, so "compressed fits where stored did
  not" is a fact about the rule rather than an accident of one retail map: 9,051
  B of authored 64x64 terrain compresses to 1,148 B, and against a 1,536-byte
  reservation it REPLACES where the old rule relocated. The other four keep that
  one honest -- the row is marked 8 and `gwdat` decodes it back to the exact
  authored blob, the HEAD row is untouched, a map past its reservation even
  compressed still RELOCATES (compression does not obviate `datmove`),
  `--stored-install` writes the authored bytes verbatim marked 0 as the control
  arm, and the SABOTAGE flips one byte of the declared `--expect` payload and
  requires the writer to refuse with the archive byte-identical afterwards --
  which is the only refutation that exists, since the entry crc is over the
  STORED bytes and `datcheck` has no notion of a compression code. The row is
  read back by a walker written out of `int.from_bytes`, sharing no code with
  `archive.py`. Section 4 measures the gain per size (20.2% / 12.7% / 9.7% at
  32/64/96) and bounds it only as "strictly smaller", because a pinned number
  would go red on an encoder change that was an improvement. Section 5's AST
  pins MOVED with the dispatch rather than being weakened: `main()` must CALL
  `install_partner`, `install_partner` must reach both writers, still without
  `--check-overlaps` and now with `--compression` AND `--expect` in both
  argument lists. **Section 8 is the map that displaces nobody** (2026-08-20, WORLDMAPS-W3).
  Every authored area before it rode map 143 -- MFT rows 71496/71497, a live
  retail area in the owner's own copy that nothing in this repo can name
  (FINDINGS 16-P7: there are ZERO provably-dead rows) -- because `datwrite` and
  `datmove` both start from a row ArenaNet made. `deploy.py --install` now
  ALLOCATES the chain instead when the area's map row carries `created = true`
  and its file id binds nothing: `create_streams` builds `[Stream(b"", 259),
  Stream(gwenc_stream, 1, extra_bytes=8, expect=plain)]` and `create_chain`
  drives `datalloc.plan_alloc`/`alloc`. What makes this section different from
  section 7 is that its failures are SILENT -- section 7's are loud (a row holds
  the wrong bytes, a verb did nothing), while a file id registered on the PARTNER
  instead of the head passes every crc rule and all ten of `datcheck`'s
  open-time rules right up until the client's reconcile deletes the head and
  frees its extent, and a row below `FIRST_CLAIMABLE_ROW` is handed to somebody
  else at the next launch. So the created rows are read back by this file's own
  `read_next` and `read_id_pairs`, written out of `int.from_bytes` and sharing no
  code with `archive.py`: the head is flags 259 and ZERO length with no extent,
  the partner is flags 1 marked compression 8 and `gwdat`-decodes to the exact
  authored blob, the head chains to the partner and the partner terminates, the
  id names the head and NO id names the partner, and both rows sit at index >=
  16. The fixture's declared row count was raised 6 -> 16 for exactly that last
  rule: `plan_alloc` refuses a chain linked below 16, so six rows would have
  failed for a reason about the FIXTURE. Four refusals are driven, each on its
  own hand-laid archive: an id bound to a non-map-chain shape (flags 3 on stream
  0) is refused naming the row and its flags; an id whose BIT-31 SIBLING is bound
  is refused before the allocator sees it, with a control proving the fixture
  really is the dual-registration shape the default `file_id_table` would hide
  (`plan_alloc` tests exact membership and would accept it -- that gap is
  studies/archivewrite FINDINGS 17.5, still open, so the CALLER refuses); an
  absent id on a row WITHOUT `created = true` keeps the old refusal, because
  "resolves nowhere" is also what a typo looks like; and a resolving id falls
  through to the install path, which is then RUN -- a second deploy replaces in
  place, so a created row is an ordinary row the moment it exists. Two sabotages:
  one byte of the declared payload flipped is refused through the create path
  before the plan is even computed, archive byte-identical afterwards; and a
  chain handed over PARTNER FIRST is refused by the allocator's own shape loop,
  driven by hand because `deploy` cannot express it, which is the claim. **Two
  of section 8's checks are about a RUN NOTE rather than about bytes, and they
  are there because a skeptic ran the command** (2026-08-20): W4's step 1 is a
  build-only run whose output the operator compares against a prediction
  registered beforehand, and it printed nothing about the row -- `create` is
  computed only under `--install` (deciding costs a refusal; a dry run must not
  refuse) and the create line was printed under that same decision, so a CORRECT
  dry run against an unbound id was indistinguishable from a broken
  area -> map row -> file id join, i.e. it read as a refutation. `create_note` now
  answers on every run and this section drives all four of its states -- the
  build-only line names the id and says `--install would CREATE`, the `--install`
  line is unchanged, an unbound id on a row that did NOT ask previews the
  REFUSAL, and a bound id says nothing because `verify()` already did -- plus an
  AST pin that `main()` calls it OUTSIDE any `create`/`install` test, with the
  sabotage that wraps it back up in `if create:` and makes that pin red (the
  sabotage's search string is newline-anchored: without that it is a substring of
  its own replacement and produced an IndentationError instead of a clean red).
  The other pair covers `spill_stream`: `install_partner` HAD to write
  `<area>.c8.bin` because both CLI writers take `--data FILE`, `create_chain`
  did not because `datalloc` takes bytes, so the path that needed the file least
  was the only one producing it -- backwards, since after an install the row is
  itself a second copy while a created chain the client rewrites or deletes
  leaves none. The create path now spills before the plan (so a refused
  allocation still leaves what was refused) and a STORED write still spills
  nothing. The content round-trip loads `[map.166]` (file id `0x5F0B0`,
  `created = true`, source `invented`) and `[area.frontier]` (64x64, sculpt's
  donors by FILE ID) and checks the server's `map_static_config` still builds --
  and that frontier does NOT ride map 143, because deploy joins area -> map row ->
  file id and an area pointing at 143 would install into the displacement row and
  never reach the create branch. Finally main() must CALL both
  `resolve_or_create` and `create_chain`, asked of the syntax tree with the
  sabotage that flips it, for section 3's reason. **Section 6b is the serve
  verdict, and it exists because a correct run was reported as a failure**
  (2026-08-20, WORLDMAPS-W2). `spawn_population` has TWO legitimate exits --
  `area 'X': N of M placed` and `area 'X': no population rows; the world is the
  player and the geometry` -- and `PLACED_RE` matched only the first, so the
  second fell through to the arm written for a server that CRASHED mid-placement
  and printed "the server never got as far as placing bodies". BOTH arms of W2
  hit it: each had served the mesh correctly (55 trapezoids, the server's own
  count against the archive's), and each exited 1 saying "the client walked on
  our map and the server did not", which was false. The finding survived only
  because a human read the gamesrv log and overrode the transcript. `serve_run`
  now returns one of three VERDICTS -- `SERVE_PASS`, `SERVE_UNPOPULATED`,
  `SERVE_FAILED` -- and `main()` returns 1 from exactly one branch, which tests
  `SERVE_FAILED`. The load-bearing claim is the ORDERING and it gets its own
  checks: an empty area may downgrade a PASS to SERVED-UNPOPULATED and may NEVER
  lift a FAILED, driven with the real pair (ArenaNet's 27-trapezoid build of map
  143 against our 55) from both sides, plus the no-`--area` case where the mesh
  is the entire verdict. `serve_run`'s decision is pure -- read a log, choose a
  verdict -- so it is tested BEHAVIOURALLY on canned logs with `launch` and
  `newest_harness_log` stubbed, rather than on the syntax tree: the two clients
  and the 45-second hold are the only reason it was ever untestable. The regexes
  are checked DISJOINT in both directions (they share the `area 'X':` prefix,
  which is how one swallowed the other's line), and `UNPOPULATED_RE` is matched
  against the line `authsrv` ACTUALLY BUILDS -- reconstructed from its syntax
  tree by `render_fstring`, not against a copy pasted into the test -- because
  the pattern hard-codes eleven words of another module's prose and a reword
  would otherwise break it silently. The other half is a SECOND READER:
  `spawn_row_count` mirrors `area_population`'s two predicates (the row names
  the area, the row is enabled) and `serve_run` refuses when it disagrees with
  the server, in either direction. Without it SERVED-UNPOPULATED would be a
  verdict that cannot fail -- the server says "nothing here", we write it down,
  green -- and a population that genuinely went missing would read as a clean
  run. Its own suppression is deliberate and narrow: under `--repo-content-only`
  deploy's world is narrowed and the server's is not, so the count is not
  claimed at all rather than compared against a world it does not describe. All
  twenty of this section's checks were driven RED by eight sabotages, including
  the original defect restored and the authsrv reword. **Section 9 is the row's own HEADROOM,
  declared by the area** (2026-08-20, WORLDMAPS-W5), and its headline arm is a
  case that could not happen in this tree the day before. A compressed install
  writes the size field and so SHRINKS a row's reservation; `resolve_rows`
  recomputes the ceiling from the CURRENT size; and the 24-byte MFT row has no
  entitlement field, so "what this row was given" survived nowhere.
  `install_partner` therefore relocated -- always, even into a chain we created
  ourselves, whose partner was born with zero headroom by construction.
  `datwrite`'s `grow_to` was the flag for exactly this and had one caller,
  `restore()`. An area may now declare `reserve_bytes`, and deploy honours it in
  both directions: creation asks `datalloc` for that many blocks, and a later
  install past the row's current reservation but inside the budget runs
  `--replace --grow-to` instead of `datmove`. The section drives all three
  outcomes over ONE archive, in the order an author actually produces them, so
  each verb is judged against the row the previous one left behind: created with
  a 2,048 B budget (the row zeroed to the end of it, where this fixture fills
  unclaimed space with 0xCC, so the reservation is real rather than the 1,536 B
  a 1,148 B payload would have taken), and `resolve_rows` then reporting that
  row's ceiling as 1,536 and NOT the 2,048 it was given -- which is the
  entitlement-not-recorded fact as a MEASUREMENT rather than a quotation; then
  1,952 B GROWING BACK IN PLACE at the same offset; then 2,744 B RELOCATING and
  saying which budget it is past; then 1,148 B simply FITTING, the ordinary arm
  untouched. **THE BUDGET IS HALF A GATE, and both halves have a control.**
  `--grow-to` is a statement about what a row was GIVEN: for a chain this
  toolkit allocated the area's budget IS that statement, and for a RETAIL row we
  are displacing it is not -- annexing the blocks behind ArenaNet's row because
  our recipe declares a number would be inventing an entitlement. So
  `install_partner` requires `reserve` AND `created`, and the section runs the
  SAME install three ways, one field apart each time: no budget relocates (as
  every run of this command did before today), budget plus `created` grows in
  place, and budget WITHOUT `created` relocates again and has to SAY the budget
  went unspent -- the one relocation whose cause is a rule rather than a size.
  `budget_note` mirrors the same two fields, because a preview that promises a
  grow the install will not attempt is worse than no line at all. **And the
  refusal is checked as hard as the success.** `_grow_gate`'s first condition is
  that no other live row has taken the blocks this one freed, which is a fact
  about the archive; a fallback that swallowed it would turn a claimant conflict
  into a relocation that quietly worked. So `build_archive` gained an
  `extra_rows` hook, a squatter is planted in the very block the row would
  annex, and the run has to PRINT the gate's own sentence and name it as the
  reason before relocating -- with the squatter's 300 B asserted untouched
  afterwards and the squatter-free fixture growing cleanly as the positive
  control. The recogniser is checked both ways (an ordinary refusal is not a
  gate refusal; each of the four markers is), and then the case that matters
  most: a grow whose declared payload has one byte flipped PASSES the gate --
  the blocks really are free -- and fails on the declaration, which must be
  RAISED rather than relocated around. **That arm is asserted on the NEGATIVES,
  and the reason is a defect this file shipped with for a day.** "It raised" and
  "the archive is byte-identical" both hold even when the recogniser is broken
  to accept ANY failure, because `datmove` independently refuses the same lie
  and re-raises the identical sentence with nothing written -- MEASURED, by
  breaking it: the run printed "THE GROW GATE REFUSED: <a temp-file path>",
  relocated around a bad declaration, and stayed green. What catches it is what
  the run SAID: the captured output must contain neither the gate's headline nor
  "RELOCATING instead". Where two independent refusals guard the same bad input,
  a positive-only assertion measures the second one. Because `verify()` predicts
  a verb from the row's CURRENT reservation and would contradict the install for
  precisely this new case, the budget gets its own preview line, `budget_note`,
  driven through all five of its states. The content round-trip requires
  `reserve_bytes` to load as a whole number of 512-byte blocks (datalloc refuses
  a fraction), to be at least the 2,828 B of the largest compressed partner this
  toolkit has MEASURED, to read as zero on an area that never asked for one, and
  to sit on a maps.toml row carrying `created = true` -- the only kind of row it
  can be spent on. `deploy.area_reserve` is where content becomes a number and
  is therefore where a bad one is refused: `2048.5`, `"8192"`, `-512` and `True`
  each name content/areas.toml, because `int()` truncates the first silently, the
  third is falsely truthy all the way to a printed line, and the INSTALL path
  never builds a `datalloc.Stream` to catch either. A budget under its own
  payload must reach the operator as `deploy.Refused` and not as a traceback --
  `create_streams` builds a Stream, so the create path gained a raise site
  `__main__` cannot see, and the check asserts the TYPE by module and name since
  both classes are called `Refused`. Finally `main()` must pass BOTH keywords --
  `reserve=` to the two writers (the create path chooses the ceiling, the install
  path spends it) and `created=` to `install_partner` and `budget_note`, whose
  absence is silent rather than red -- asked of the syntax tree, with a
  rename-not-delete sabotage per keyword so the calls stay parseable and only the
  keyword goes. Four sabotages driven by hand, all red: the recogniser accepting
  any failure (3), `created` dropped from the gate (3), `create_streams` back
  outside the refusal (2), and `area_reserve` reverted to a bare `int()` (4).
  **Section 10 (2026-08-20) is the RESIDUAL pass -- the guards WORLDMAPS-W3 left
  open plus one deferred from W5, floor 167 -> 203 across a build and a fix.**
  (1) THE BORN-ARMED GUARD WAS LIVE CODE NOTHING EXERCISED: three lines inside
  `main()`, reachable only with a vault, an archive, a donor and a content row.
  It is `deploy.head_is_armed` now -- the same question on the same field at the
  same moment -- and both answers are driven on real fixtures: a displaced
  retail head (300 B) is not armed, a created head (0 B) is, and writing content
  into that SAME created head flips it back, which is the case the guard exists
  for and the reason it asks the ARCHIVE rather than the `create` flag.
  `main()`'s branch is pinned on the syntax tree -- the INNERMOST `if`, because
  the first version of the finder reached `if args.install:` and asked every
  question about the wrong branch -- with two sabotages: pointing `already` at
  `create`, and inverting the test. (2) `resolve_or_create`'s fall-through fired
  IDENTICALLY for our created chain and for a retail chain that happens to bind
  the id, because `map_chain` checks SHAPE and 349 retail maps in the owner's
  own copy have that shape -- so `created = true`, a claim `content/` makes
  against no archive in particular, displaced a live ArenaNet area while every
  line of output said the word "created". It takes the allocation journal as
  EVIDENCE now, read STRUCTURALLY rather than as prose (the lesson of the
  grow-gate join, one item down): the journal must carry an edit whose bytes are
  exactly `<II`(file_id, head_row) -- the file-id record going live, step 4 of
  the allocation and the moment the chain acquires its name -- and write 24-byte
  MFT rows at the journal's OWN recorded `mft_offset` (not today's: the client
  relocates the table during ordinary play) with the head's flags chaining to
  the partner and the partner's flags. **THE FOURTH CONJUNCT -- is this journal
  about the archive in front of us -- WAS A PATH COMPARE, AND THAT WAS ITS OWN
  BUG; a skeptic's probe found it and the fix pass closed it.** `datalloc`
  records an ABSOLUTE path, and archives here are copied WHOLE as a matter of
  routine (`overlay.py`'s `shutil.copyfile`, `make_run_dir.py` staging a run
  directory, RUNBOOK's `Copy-Item run-live\<build>\Gw.dat run\<build>\Gw.dat`),
  so an honest re-deploy of OUR OWN chain on a copy -- journal travelling beside
  it, describing the copy byte-exactly -- was REFUSED, and the refusal's closing
  line told the operator to allocate under a fresh id: wrong advice in the one
  state where the chain is provably ours. The archive is asked DIRECTLY now
  (`deploy.archive_carries`, eight bytes and a seek): does it carry, at the
  offset the journal recorded, the file-id record the journal says it wrote
  there? That survives a copy, a rename, an `--out` that moved the build
  products, and a later relocation of the partner, and it is a stronger join
  than a filename in any case. The PATH compare is KEPT as the first route and
  has a fixture of its OWN -- an archive that stayed put while the id table
  moved under it, record zeroed, journal still naming the file -- so the two
  routes cover different failures and neither is vestigial. The refusal names
  bringing the journal to the archive BEFORE the fresh-id last resort, and a
  check pins that ORDER rather than the words. **AND EVERY CONJUNCT HAS A
  FIXTURE, which is the other half of the fix.** The first version asserted
  "change any one of the four and it stops being evidence" from one line that
  varied (archive, id, partner+1) -- three, not four, and `partner+1` is refused
  by the presence test -- so a mutation sweep could DELETE the head-flags test,
  the nextStream test or the partner-flags test with the section still green:
  R5's own shape, one function over. One bent journal each now (259 -> 3,
  nextStream 17 -> 18, partner 1 -> 3), plus the CONTROL that the same rewrite
  machinery putting a field back to the value it already had is still evidence,
  so what the three refuse is the BENT FIELD rather than the rewrite. Sweep
  after the fix, run rather than argued: dropping id, headflags, nextstream,
  partnerflags, the path route or the byte route each reddens 1; dropping the
  binding entirely reddens 2; `archive_carries` returning True for anything
  reddens 3. THE CASE THIS MUST NOT BREAK -- the idempotent re-deploy, the loop
  an author actually runs -- is its own check on the original AND on a
  whole-file copy, and so is the control that a row WITHOUT `created = true` is
  untouched, since displacement is what this command has always done. (3)
  `datalloc`'s CLI has refused to overwrite an allocation journal since it was
  written and `create_chain` calls `alloc()` directly, so a second create with
  the same area name truncated the first run's undo record and then printed the
  file it had just destroyed as the way back. Refused now at deploy's own write
  site, FIRST -- before the spill, before the plan, before any file is touched
  -- quoting datalloc's reasoning rather than paraphrasing it, with the journal
  and the archive both asserted byte-unchanged afterwards. (4) Three of
  `map_chain`'s five raise sites had NO fixture at all: `nextStream == 0` (where
  `MapIndex.partner` reads `by_row.get(nextStream)` and would resolve row 0, the
  file header, rather than None), a partner absent from the MFT, and a partner
  carrying the wrong flags. One fixture each, all from `build_archive`'s
  existing `extra_rows` so no fixture parameter was added, plus the unmodified
  archive as the CONTROL that the three refuse the DEVIATION rather than
  refusing everything. (5) The grow-gate join is typed (see `test_datwrite`
  §13): a writer output carrying only `GROW-GATE-REFUSED condition=...` is
  recognised, a REWORDED condition-1 sentence carrying the token is recognised,
  an older writer with the sentence and no token still is -- the four-fragment
  list is the documented fallback rather than vestigial, and a vault copy or a
  bisect is exactly where it bites -- and an ordinary refusal is still not a
  gate refusal either way. When both are present the HUMAN sentence is what
  comes back: the token is the decision, the sentence is the report. Sabotages
  driven by hand across both passes, all red: the evidence check disabled (2),
  the journal-clobber check disabled (3), `head_is_armed` made unfalsifiable
  (2), and the eight-way conjunct sweep above.
  **Section 11 (2026-08-21) is `readback`'s optional-chunk loop asserted in the
  direction it used to `continue` past, floor 203 -> 213.** The loop over the
  optional payload chunks (`0x20000009` environment, `0x20000012` sound) read
  `want = staged.find(scid)` and then `if want is None: continue`, so an area
  declaring `environment = false` had its environment assertion SKIPPED rather
  than INVERTED -- a check that cannot fire, found by an adversarial pass on
  WORLDMAPS-W8. That run installed exactly such a map, `readback` printed a
  clean 6/6, and it had said nothing whatever about the environment; the fact
  the arm actually turned on -- that the client's COMPILED map carries no
  `0x20000009` either, so there was no donor, global or cached environment to
  fall back on -- was recovered by hand out of the allocation journal
  afterwards. That fact is what makes "we removed X and nothing changed" mean
  "X was not the cause", and unasserted the null is a statement about an
  instrument that never looked. An omitted chunk now produces a row asserting
  the compiled map carries none either, and the row SAYS so in the log. The
  section drives the loop on a hand-laid archive whose one map head IS the
  "compiled" map this file assembles -- one plane, one trapezoid spanning the
  whole 32x32 field, so the mesh rows are answered by real geometry rather than
  skipped, which would have put the section in the same shape as the defect.
  Four arrangements, one field apart each: authored-and-carried still PASSes
  clean (the pre-existing assertion, shown not to have been paid for); a
  compiled environment one byte short of ours goes red naming that row and only
  that row; ABSENT ON BOTH SIDES gets a PASSing row, with the clean verdict
  asserted TOGETHER WITH the row's existence and a count that the absent arm
  prints as many rows as the present one, because clean-with-nothing-said is the
  whole failure; and the SABOTAGE -- a compiled map carrying an environment we
  never authored -- goes RED. That last arm is the load-bearing one and it was
  MEASURED against the pre-fix loop, where it returned `bad == []`,
  indistinguishable from the honest absence. Sound is driven the same pair, so
  the inversion is shown to be the LOOP's rather than one chunk id's, and an AST
  check pins that both paths reach `row_()` so a third id added to the tuple
  inherits both directions. `verdict_of` finds a row by substring and requires
  exactly one match -- an arm that produced NO environment row would otherwise
  read as one that produced a passing row, the defect wearing a different hat --
  and strips the quoted row's own marker before it goes into a check's detail,
  which is what keeps the log at one marker per line. Sabotage sweep, run rather
  than argued: reverting `readback` to the bare `continue` reddens 8 of the 10,
  and the 2 that stay green are exactly the regression guards on the unchanged
  present-path. NOT touched, and named here so it is a decision rather than an
  oversight: the height-field and prop rows are still conditional on the
  compiled chunk existing. They are a different question -- nothing declares
  those optional, so the fix there is an unconditional assertion, and it needs
  its own evidence about what the compiler always emits.
  Sections 0-1 and 3-13 need no vault and score 226 against a floor of 230 (both
  MEASURED 2026-08-21, the vault-less one with `RURIK_VAULT` pointed at an empty
  directory, which exits 1 naming the 4-check shortfall), so the floor still
  does what it was for. Per section, counted from the log rather than predicted:
  {0: 3, 1: 3, 2: 4, 3: 8, 4: 8, 5: 6, 6: 10, 6b: 20, 7: 15, 8: 36, 9: 55,
  10: 36, 11: 10, 12: 5, 13: 11}. Section 1 is 3 since WORLDMAPS-W17 added the 'ramp' generator.
  **Count the log with the subprocess writers' own lines EXCLUDED, and note
  there are THREE producers rather than two**: an unanchored
  `grep -c "\[PASS\]"` reads 247 where the ledger says 230, because
  `datwrite --verify` prints a `file header crc` line AND an `MFT self-crc` line
  per run (6 runs, 12 lines) and `datmove` prints one `0 overlapping row pair(s)
  afterwards` per move (5 moves, 5 lines). 247 - 17 = 230; anchoring the grep at
  `^  \[PASS\]` drops datmove's five, which carry no indent, and reads 242 =
  230 + datwrite's 12. An earlier version of this note said 162 from two
  producers and was wrong on both counts, so re-measure these rather than
  adjusting them. Section 11 is the one place a check's DETAIL quotes another
  producer's row, and `verdict_of` strips the marker so both greps still agree:
  MEASURED, `grep -o` and `grep -c` each read 247.
  **Section 12 (WORLDMAPS-W12, 2026-08-21) is a failure that wore the wrong
  name.** `--install` arms a map's head to zero length so the client must
  recompile it; when the client never runs, the head stays 0 B, and `readback`
  handed those bytes to the FFNA decoder, which raised about a 5-byte header
  from three layers down. A launch collision produced exactly that -- another
  session held the harness ports, `harness rc 1` scrolled past, and the run
  ended on a stack trace naming neither the map nor the cause. An empty head is
  now a named FAIL row carrying the file id, the zero length, and a pointer at
  the harness rc and `Gw.log`. Its four checks come with the CONTROL that earns
  them: a head the client DID re-bloat still produces the whole clean readback,
  because a guard that reddens the healthy path would be worse than the
  traceback it replaced, and nothing in the failing arm can tell the difference.
  **Section 13 (WORLDMAPS-W13 recon, 2026-08-21) is three holes that composed
  into one failure**: `serve_run` could reach a verdict from ANOTHER SESSION's
  log, about a DIFFERENT MAP, after a harness that FAILED. `vault/captures/
  harness/` is shared by every session on the machine and `newest_harness_log`
  took the newest `gamesrv.log` by MTIME across all of it; `fid` off the navmesh
  line reached only the note string, so `hits[0]` was read and its map never
  compared to ours; and `rc` from `launch` likewise lived only in f-strings.
  None was hypothetical -- MEASURED that day with THREE worktrees driving one
  harness, 12 of the 14 most recent captures belonged to other trees and one was
  75 seconds NEWER than this session's last run, so a `--serve` issued right
  after would have scored off a peer's log. The fix keys on the `source:` line
  `authsrv` prints, which names the worktree. **The attribution half is tested
  against REAL FILES, not the `FakeServe` stub** -- a stub cannot get
  attribution wrong, and the defect is reproduced as a live CONTROL: unfiltered,
  `newest_harness_log` still returns the foreign log, which is what shows the
  fix is about attribution rather than ordering. Two further controls keep the
  healthy path honest: our map's line among a foreign one still PASSes, and the
  plain case is unchanged. One self-inflicted lesson is recorded in the section:
  setting `RURIK_VAULT` is not enough, because `vaultpath` memoises the answer
  in a module global -- the first version leaked the temp vault into section 2
  and turned it into a declared SKIP, which the floor did NOT catch because the
  floor had risen enough to hide four missing checks behind eleven new ones.
  (The line this replaces said "score 10 against a floor of 14", stale by two
  floor changes) **§15 (MOVECODE-1z-bf, 2026-09-04): `on_mesh()`** — containment OR within `SEAM_TOL` of a trapezoid, the mesh as the client resolves it at its edges. A synthetic square pins the shape (inside agrees with `walkable`; 0.5 u outside an edge is ON, 1.5 u is OFF, the tolerance is a radius the caller owns, far stays off, and `SEAM_TOL` is still the portal test's 1 u, no new constant); on Pre-Searing the THREE report points RUN-1zBD's body stood on at the wedge tip — outside every trapezoid by exact containment, on the mesh within 1 u — and the server's legacy belief 144 u east of them, genuinely off, stays off. Floor 89 → 97 from the green run (101 checks, 5 skips) **§15i–k (MOVECODE-1z-bg): `plane_near()`** — inside is `plane_at`, a 0.5 u sliver names the sole plane, 1.5 u names nothing; on a two-plane sliver only the report's word decides and with no word it says nothing (inside, the stacked case stays `plane_at`'s own); the three wedge-tip reports are named 0/29/29 as the client reported them. Floor 97 → 100),

=== AMENDMENT 3 of 3 — test_contentids, section 6 and the floor (builder's, unchanged) ===
  `toolkit/mapdata/test_mapscale.py` (the authored-map SCALE ladder, `mapscale.py`,
  which answers "how big can an area be" with measurements instead of the two
  things that were available before: a disassembly-derived cap nothing has ever
  approached (`dim_x*dim_y <= 2^24`, i.e. 4096x4096 square) and three compression
  points at 32/64/96. The module IMPORTS `deploy`/`stripbuild`/`datplan`/`datalloc`
  and edits none of them, so what this file checks is arithmetic over somebody
  else's proven pipeline -- plus the three things that are not arithmetic.
  **Section 2 is the whole reason the module has the shape it does.** `snap_block`
  is a ONE-TILE function -- handed a whole field it projects the first 1,024
  samples and leaves every other tile's curvature alone -- and that bug shipped
  once and hid behind the worst-error statistic, because a linear field
  round-trips exactly whether or not anybody snapped it and only CURVATURE is
  lost. MEASURED here on one 64x64 wobble field: `snap_block` over the whole
  field reports worst error **4** and round-trips **2,060 of 4,096** samples;
  `snap_field` reports worst error **4** and round-trips **4,096 of 4,096**. The
  statistic is IDENTICAL and the per-sample count separates them by 2,036
  samples, so every rung carries the count and the section asserts all three legs
  -- the two worst errors agreeing (the blindness, measured rather than
  remembered), the count going red on the half-snapped field, and the CONTROL
  that it stays green on the snapped one, without which "refuse everything" would
  pass. `measure(heights=...)` exists for exactly this: a supplied field is NOT
  snapped, because projecting it first would erase the difference the column
  reports, and `snap_worst` comes back None rather than 0 since 0 would be a
  claim. Section 0 pins the dims gate as TWO INDEPENDENT WALLS and proves it in
  both directions: 8192x2048 clears the area cap exactly AND the tag-0 per-axis
  byte cap exactly and is ACCEPTED, while 8224x32 is 1.6% of the area cap and is
  still refused, because `8224/32 - 1` is 256 and tag 0 gives each axis one byte.
  It also proves the gate runs BEFORE an assemble is spent -- a six-rung ladder
  costs real seconds a rung -- by replacing `deploy.assemble` with a raiser and
  requiring `ladder([32, 48])` to come back with `_gate_dims`' own "not both
  multiples of 32" rather than the raiser's AssertionError. **Section 3 is about
  what a report stops being able to ANSWER, and both of its guards were added
  after review found the module failing its own stated rules one field away.** A
  `Capacity` loses its run list through JSON and keeps its summary, so `fit()` on
  a restored one returned `(blocks, None)` -- and `Rung.lines()` renders a None
  run as "NO usable run in this copy is big enough", which is the identical text
  a MEASURED refusal prints. Measured against the c2 copy: live `fit(4820)` ->
  `(10, (118658, 10))`, restored -> `(10, None)`, with `largest_usable_run_bytes`
  still reading 953,856 -- a fabricated refusal for a stream the same object's
  surviving summary says fits 197 times over, from the module whose docstring
  says "IT NEVER QUOTES A CAPACITY FIGURE FROM A DOCUMENT". A restored capacity
  now carries `from_document` and REFUSES, naming `--dat` as the remedy, and the
  section checks that beside the CONTROL that a measured capacity still places
  the same stream (a measured copy with genuinely zero usable runs must keep
  answering None, which is a finding). The second guard is the same sin from the
  other side: `Rung.from_dict` policed UNKNOWN fields while `Rung.__init__` fills
  absent ones with None, so `Rung.from_dict({})` was ACCEPTED and
  `snapped_exactly` reported a perfect round trip because `None == None` -- and
  that property is what `main()` sets its exit code from, so a truncated or
  older-version report read as every rung surviving the codec. `from_dict` now
  requires the whole field set and names what is missing, and `snapped_exactly`
  refuses over a None rather than answering, which is the belt to that brace
  since a field can be PRESENT and explicitly null. Each is checked with its
  control (a rung that HAS both numbers still answers True), because a guard
  whose failure mode is silence is exactly the kind "refuse everything" would
  pass. Section 4 needs the vault and carries the RECONCILIATION that makes the
  ladder trustworthy: with the plaza row's own configuration (5 trees, seed
  `1536,1536`) it reproduces `deploy.install_bytes`' measured table TO THE BYTE
  at all three of its dims -- 3,941->1,316, 10,654->2,012, 21,786->2,828 -- so
  this is a measurement of deploy's pipeline rather than of a re-implementation
  that drifted, and at `--trees 8` it likewise reproduces WORLDMAPS-W4's frontier
  (10,714->2,028). The SEED is load-bearing and that took finding: the Path chunk
  carries the boundary point verbatim, so moving it changes no byte COUNT and
  changes which bytes, and compression 8 notices -- at each rung's own centre
  64x64 measures 2,008 rather than 2,012. The same section measures one archive
  copy's capacity FRESH (free runs, MFT slack, id-table slack) and asserts only
  RELATIONSHIPS, never a remembered number, because every one of those figures is
  play-history state that expires the next time the copy is played; the MFT-slack
  check is re-derived from the archive's own geometry (size plus slack lands
  exactly on a block edge, slack under one block) rather than restated as
  `rows*24 + remainder`, which could not fail. Its closing check is section 3's
  restored-capacity guard run against the REAL copy and the real stream size. The
  default ladder is small on purpose -- 32 and 64, one 64, three dims against the
  copy, about 3.5 s -- and the big rungs (128/192/256) are section 5 behind
  `--big`, because the suite runs constantly and a rung nobody is waiting for
  gets skipped by a person instead of by a flag. Floor 62, MEASURED (the first
  draft guessed 47, the run scored 54, and section 3's two restore guards took it
  to 62): 48 checks with no vault in reach, 62 with, 66 under `--big`. Three
  hand-driven sabotages have each been run red -- restoring the pre-fix `fit()`
  reddens two checks, the pre-fix `from_dict` two, the pre-fix `snapped_exactly`
  one, every control staying green),
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
  that ArenaNet's own row 46196 passes all **18** before anything we built is judged;
  five rules are then broken on purpose and must go red ALONE. **18, not the 17 this
  entry said until 2026-08-18** — the 18th came out of FINDINGS 30 (*every REACHABLE
  plane above 0 names a prop that exists*), the rule added after a bad `plane_map`
  crashed a client twice, and it is what the authored portal's arms are scored against
  in customarea §31. The completeness check was `len(result) >= 17` while the set was
  already 18, so **that gate could have been deleted with the check still green**; it
  now pins `GATE_COUNT` exactly and goes red on either direction, verified by
  mis-stating it. Section 2 also refuses
  `--out` into EVERY checkout of this repo rather than the one the file sits in: a
  git worktree's repo root is not the main checkout's, and until `working_tree_roots`
  existed a build written to `<main>/toolkit/` was allowed straight into version
  control. Sections 0-3 score 46 against a floor of 98, so a vault-less run goes
  red. ~12 s),
  `toolkit/authsrv/test_spawn_burst.py` (the nine messages that put a body in the
  world, and since 2026-08-15 **the one that killed the client**. The
  column-major section (§5 today, §4 then) used to read `0x003A`'s payload at
  a stride of 3 — `triples[0::3]` for the ids, `[1::3]` for the ranks — which
  is our builder's layout checked against itself,
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
  agreeing with ourselves and would pass on any self-consistent layout.
  **TWO sections were rebuilt on 2026-08-21, and the second is the cautionary
  one.** The old section 3 read one constant — `authsrv.ATTRIBUTE_POINTS == 0`,
  the 8-of-8 live value — and `84fd41d` turned that constant into per-character
  state at 08:55 on 2026-08-20, so this file spent a day raising
  `AttributeError` while being named in TESTS.md as part of the suite. **The
  burst still sends `0x0037`, so the fix was not a deletion**: the new §4 builds
  the same `attribspend.AttributeState` the burst builds — a bare `{}`
  connection state, no socket and no store — and pins the balance the server
  actually puts on the wire. 200 lifetime, **173 priced off the client's own
  cost curve rather than typed in** (the test re-sums `s_attribPoints[1..rank]`
  itself), 27 unspent; that the ranks are AFFORDABLE, which is the question
  `content/world.toml` said out loud that this server could not ask; that the
  two fields are DIFFERENT numbers, which is the 2026-08-19 bug (one value in
  both slots told the client every point was unspent while handing it ranks that
  had cost some); that field 3 <= field 4, the 48-of-48 corpus invariant that
  settled the CONTESTED field order; and a CONTROL requiring the swapped order
  to break it. Collapsing `available` to `points_total` reddens four of them,
  the CONTROL included.
  **Section 5's defect was worse, because it was GREEN.** It called
  `attribute_columns()` with no arguments while the burst calls
  `attribute_columns(live_ranks, bonuses)` — a binding that invokes a different
  overload than the caller under test binds nothing. The two diverged at 10:23
  the same day (`8b50ca1`), and by exactly the finding of that commit: column 3
  is base **plus equipped gear**, so the starter hammer's `+1` makes Hammer
  Mastery go out as 7 over a base of 6, which is what the client drew in capture
  `20260820T113942`. The section now calls what the burst calls, and its new
  check requires at least one column-3 gap to actually BE +1 — the one check
  that can tell the two calls apart, since with equal columns they are
  indistinguishable. Deleting the bonus from `attribute_columns` reddens three.
  Floor 34 -> 38 -> 48. No socket, no client. ~1 s),
  `toolkit/authsrv/test_attribspend.py` (the attribute SPEND model -- the state this
  server had never had. Until 2026-08-20 ranks came from a content row and never
  moved, and `studies/review` had years ago flagged the consequence: "you sat there
  spending attribute points and the server had nowhere to put them." The rules it
  checks are ArenaNet's, not ours, and the file is built so a copy of somebody
  else's rules cannot quietly drift into being its own thing. **Nothing is
  hand-typed**: it loads the same two content tables the server loads -- the cost
  curve from `s_attribPoints` and the 51-row `s_attrib` table -- and checks them
  against arithmetic published independently of both. Rank 12 costs **97**, the
  number the wiki and the client's table agree on; **exactly ten** attributes carry
  `is_primary`, one per profession, which is the no-free-parameter check that the
  table was parsed right at all. §5 is the one to read: it REPLAYS the nine real
  rank transitions in live capture `20260818T132739` -- six up, three down -- and
  requires this module to reproduce the balances ArenaNet's own server computed
  (74->65->54->41->25->5 climbing 7->12, and 5->25->41 coming back), which pins the
  ASYMMETRY that the price is the rank REACHED and the refund is the rank LEFT.
  The rest covers the client's three refusal rules from the ALLOWED side as well as
  the refused one -- a Warrior may raise Strength, may not raise Divine Favour even
  as a secondary Monk, but may raise an ordinary Monk attribute -- so the refusals
  cannot pass by refusing everything. §7 pins the template spread as all-or-nothing
  against the client's own SIXTEEN-entry buffer (its framer clamps to 64, which is
  a latent stack smash we must never invite), and §8 breaks the constructor on
  purpose: no costs, no attributes, and a GAP in the rank sequence all refuse,
  because a gap would price a rank at 0 and hand out a free level. Floor 35, one
  declared skip (no profession-0 attribute exists to fire the first of the client's
  three refusals). No socket, no client, no vault. ~1 s),
  `toolkit/authsrv/test_purchase.py` (answering the merchant, BOTH directions -- the four
  messages, in ArenaNet's order. It pins the SEQUENCE and not just the contents:
  **pay, mint, place, confirm** -- `0x014F` debit, `0x0161` declare, `0x013E`
  move, `0x00CC` done. The first arm sent that nearly backwards and the client
  died on `Assertion: item` `ItCliApi.cpp(1883)`, which is `0x013E`'s own argument
  check failing on its first lookup. The bad order was MANUFACTURED by the tool
  that read it -- all four share one segment timestamp, a timeline script sorted
  whole tuples, and the tie fell through to the OPCODE NUMBER, so ascending
  opcodes reached a study document dressed as a finding. Within one frame, byte
  offset is the only ordering evidence there is. Checked against two
  real requests written in as literals -- ours `[1, 10, [], b'', 0, [40],
  b'']` and retail's `[1, 40, [], b'', 0, [2474], b'']` -- so a change to
  the handler cannot quietly redefine what a request is. Buying MINTS a new item
  id (retail 2474 -> 4130: stock is a catalogue, not the goods) and the copy
  keeps every declared field but the id. Six refusals with a positive control
  beside them -- undeclared item, the SELL kind on the BUY message, no item, a
  truncated request, a full backpack -- because the client has already decided
  locally that it can afford this and has room, so anything we cannot answer is
  a disagreement between its model and ours, where a plausible reply is worse
  than none. `0x014F`, the debit, is OBSERVED-ONCE and the file says so: one
  purchase was ever made in front of a capture. **SELL (`0x004A`) is the same file's
  section 6** and its trap is that the request is NOT the buy message's shape: five
  fields against seven, and the price sits at index **4** here and index 2 there, so
  reading the buy's index would credit 0 every time and do it silently. Its reply is
  three messages -- `0x014D` remove, `0x0140` credit, `0x00CC [11]` -- read by byte
  offset from all EIGHT sales, with no `0x013E` and no re-declaration because the
  item ceases to exist. `0x00CC` is last in all nine transactions, the one ordering
  invariant this family has. The backpack is asserted to be a slot MAP and not a
  cursor (a sale frees its slot, the next buy reuses it) -- a cursor would call a
  20-slot bag full after twenty transactions on an empty one. Floor 27. No vault, no
  socket, no client. ~1 s),
  `toolkit/authsrv/test_playerbags.py` (the player's nine containers, and **WHERE**
  the burst sends them. Until 2026-08-19 this server created ONE bag, and the
  symptom was not a missing grid but a missing PURCHASE: with a funded purse, a
  priced shop and Buy rendered ENABLED, an operator watched a click on Buy land
  and produce ZERO c2s traffic. The client refuses a purchase it has nowhere to
  put and refuses it LOCALLY, so ArenaNet's "inventory full" path costs no wire
  message and the null read as a missed click. Two defects hid each other -- the
  bag SET was one ninth of retail's, and the one bag we sent was created inside
  `if EQUIP_WEAPON:`, so every inventory question depended on a weapon flag.
  Sections 1-4 check `authsrv.PLAYER_BAGS` against ArenaNet's own wire through
  `invcensus.bag_shapes()` -- ONE extractor, shared with the tool a human runs,
  so a census printed by hand and one asserted here cannot disagree -- and the
  corpus is not a sample: **49 of 49 live connections carry the same nine
  (type, model, slots) triples**, one distinct set. It also pins the reading of
  the message's trailing field: nonzero on the type-1 backpack and NOTHING else,
  49/49 an item id declared by an `0x0161` in the same tape -- the Backpack is a
  real item in Guild Wars and the equipped/storage/material containers are not.
  Sections 8-9 are the ones no value can express, and they are where BOTH real
  defects lived: a SYNTAX-TREE check that the burst iterates the table outside
  any `if EQUIP_WEAPON`, and one that no loop TARGET shadows a name the
  enclosing handler already binds. Naming a target `kind` overwrote the
  connection's channel discriminator with the last bag's TYPE -- every later
  c2s message then missed `if kind == "game"`, so the client's
  INSTANCE_LOAD_REQUEST_SPAWN_POINT went unanswered (hung at 100% on the load
  screen) and its keep-alive decoded as an auth message whose handler died on
  `values[3]` (`Code=007`). Two run failures from one loop variable, with every
  number in the table correct throughout. Five controls: two break the table on
  purpose, and three feed the detectors the exact buggy source so a green check
  cannot mean the detector is blind. Floor 16; sections 1-4 print a `skip`
  without the vault. No socket, no client. ~4 s),
  `toolkit/authsrv/test_movement_fidelity.py`,
  `toolkit/authsrv/test_agentlife.py` (**`section_follow_router` is MOVECODE-1z-by (2026-09-05): the hostile's OWN copy walks a routed corridor.** The fixture is RUN-1zBW's wedge in miniature -- a `clip()` that cannot leave the corner and a `route()` that can, with the corridor deliberately running the WRONG WAY first, because that is what escaping a corner looks like and it is what trips a straight-line leash. It runs **the known-bad arm first** (`--no-npc-follow-router`: 0.0 u moved, no arrival, and zero route calls, so the arms differ in the one thing under test), then the routed arm (900 u out), then checks the two are ordered the right way round; that the corridor is CACHED (3 solves over 80 ticks, not one per tick); all four fallbacks to today's behaviour -- `route()` None, a mesh with no `route()` at all, the flag off, no pathmap; and BOTH leash directions -- our own detour must not end the chase, and a player genuinely past the leash must. Floor 268 -> 286 from a real green run of 301. **`section_npc_plane` is MOVECODE-1z-bz (2026-09-05): ANIMREF-RE §42.5's tracked plane words.** Its stub is §42.5's own PASS shape -- ground plane 0, x >= 500 plane 29, and a strip the mesh cannot name -- and it pins `(29, 0)` at the foot, `(29, 29)` after the crossing (field 4 correcting itself off a stale spawn word with no step), the mover's plane following it across, the fallback to the mover's word where `plane_at` returns None (and never -1), a pathmap with no `plane_at()` degrading instead of raising, and **the frozen-spawn-word arm as the control** -- the same crossing order reads `(0, 0)` with `--no-npc-plane-track`. It also moved the pin §42.5 said would have to move: the chase section's `fol[2] == fol[3]` is now `== agent["plane"]`, because retail's 205-of-206 `(0,0)` is a flat map rather than a constant. **`section_plane_repath` is GROUNDZ-Q5 (2026-09-06): a parked hostile whose plane went stale since its last order gets ONE zero-distance `0x0029` carrying the corrected word**, addressed to the point the client already has it on; no change means no send, a second inside `FOLLOW_REPATH_INTERVAL` is refused, a plane change MID-WALK re-paths without waiting for the player to move, and `--no-plane-repath` is the known-bad arm (the stale word stands, RUN-GROUNDZ-R1's 22 s of plane 0). Floor 286 -> 294. **`section_client_model` is NPCTRACK-Q1 (2026-09-06): the hostile's copy IS the client's own sync copy** -- `agtrack_mirror.SyncAgent` (the decoded dead-reckoner and bake this server already runs for the player's world-0) fed with the follow's own sends, plus the collision resolver's disc stop (r+r+56 inside a +-60 degree forward cone, ANIMREF-RE 38.2) in the best frame the server can compute. It pins the standing case against `section_chase`'s own 80 u (the disc solved on the leg's line, exactly), the DIVERGENCE the tapes measured (the client's frame 300 u aside: the copy walks to the ORDERED point and the disc never fires, where the revert arm parks 80 u from the server's player -- the arms differ by the 80 u the client never walked), the cone (a frame point 50 u BEHIND does not stop it), each message as the client applies it (0x0028 halts in place mid-leg; 0x002B is a pure store that the current leg ignores; GROUNDZ-F9's zero-distance 0x0029 moves nothing), the re-seed when anything else teleports `agent["pos"]`, all four frame branches, and that a copy parked out of reach of the server's player but INSIDE reach of the client's frame halts on the clock and then HOLDS -- no fresh follow and no swing until the client's belief moves, at which point a fresh follow opens (NPCTRACK-F8: RUN-R1's wire caught the alternative, a follow every 0.56 s that parked at once, 37 halts against 13). Green 333. `section_follow_router` now runs on the revert arm, since the corridor it exercises only exists there, and the chase section's wall pin is split by arm: the corridor arm is stopped by `clip`, the default never asks (the client's sync copy dead-reckons straight; the drawn body paths). Floor 294 -> 315 from a real green run of 331. **`section_plane_reach` is GROUNDZ-F11 (2026-09-06): where our mesh has NO trapezoid under a hostile, the player's own reported plane names ground within the follow's reach.** The owner's session found the Hatcher drawn 52 u into the terrace above the stairs for 16 s: every point it stood on is uncovered by our mesh, `_npc_plane` held its carried 29, and the client's height reader answered a cached value on a plane with no surface there. The section's stub (`_Terrace`, a `_Stairs` that answers `planes_at` with an empty set on the strip) pins: the measured shape (the word becomes the player's reported 0 at 60 u), out of reach (200 u: the carry stands), a seam is not silence (named ground wins even with the player in reach on another plane), a mesh without `planes_at` degrades to the carry, the PARKED branch then sends F9's zero-distance `0x0029` carrying 0 -- the send the terrace never got -- and the known-bad arm (`--no-npc-plane-reach`: the same park holds 29 and sends nothing, the operator's screenshot). Floor 315 -> 323 from a real green run of 341. **RUN-1zCE (2026-09-06) then fell off the reach test's knife edge**: the model parks at exactly `follow_stop_radius()` from the frame and the test was `<= follow_stop_radius()`, so R3's park at 79.96 u fired and 1zCE's at 80.02 u did not (7.9 s on plane 29, height cached). The slack is now the swing's own deadband (`NPC_PLANE_REACH_SLACK = BOUNDING_RADIUS`, the same 12 u by which `enemy_reach()` exceeds the disc), pinned at exactly 80.0 u and one step short of the slack's end, with the 200 u carry unchanged. Floor 323 -> 325. **`section_corridor_wire` is NPCTRACK-Q9 (2026-09-07): the follow's corridor goes ON THE WIRE.** Its stub (`_WallMesh`) is the hole above the stairs in miniature -- a wall between the hostile and the player, open to the south, `route()` going round by a corner it names on plane 29, `clip()` refusing the straight line. The known-bad arm runs first (`--no-npc-corridor`: the first order names the player, no `0x0029` is ever sent, the copy walks straight through the wall, zero route calls -- the Hatcher through the hole), then the fix: the first order is a `0x0029` to the corner carrying `(29, 0)` (field 3 the corridor's plane for the vertex, field 4 the mover's), the copy arrives there at 0.69 s and the NEXT order is the `0x002A` naming the player with the line now clear, the copy passes through the corner to 0.0 u, the chase still halts at 80.0 u, and the router is asked twice over 80 ticks (per ORDER, never per tick). Then the open (a start with a clear line: the `0x002A` and no leg, byte for byte the confirmed shape), a `route()` that raises (falls back to the agent-addressed follow), and one that answers a bare list (legs to the vertex with field 3 falling back to the mover's plane). Floor 325 -> 337 from a real green run of 355. **`section_enemy_count` is NPCTRACK-Q10's groundwork (2026-09-07): `--enemies N`.** N == 1 is today's spawn (one hostile under the standing id, its spot skipping the one point a stub mesh refuses); N == 3 puts hostiles under 10, 11, 12 -- the unallocated block -- at three distinct spots the mesh accepts, one shared definition, all hostile hatchers, three bodies on the wire; without a navmesh the spots are the compass ring at the plain offset; the flag rebinds through a declared global and is capped at 8. The entry literal moved from `spawn_enemy` to `_spawn_one_enemy`, and the two source-introspection checks that read it (`skills` here, `resend_definition` in `test_burrow`) now read that function. Floor 337 -> 344 from a real green run of 363. **RUN-1zCG (2026-09-07) added three checks:** in `section_corridor_wire`, a copy 6 u into a seam where the stub's `route()` refuses the origin is stepped onto the mesh and still gets its corridor leg (the session's three bare follows through the stairs' flank and the hole); `section_hold_plane`, a hostile parked in the CLIENT's frame (out of the server's reach, `last_report` 40 u ahead) with a stale plane word gets ONE zero-distance `0x0029` carrying its own plane and no follow opens, and a word already right sends nothing (the foot-of-the-stairs terrain walk). Floor 344 -> 348 from a real green run of 366; session 2 of RUN-1zCG added one more in `section_corridor_wire` (a corridor vertex inside the PLAYER's 80 u disc is not sent, the follow names the player: F14 halts the copy there), green 367. The rest is WORLD_REMOVE_AGENT and its two refusals,
  that an unframeable opcode stops the framer instead of being framed past, and
  the whole enemy: a hostile that swings back, chases, turns to face you and
  casts — each phase checked as a SHAPE the wire could contradict rather than as
  a message count. §4b is the `--no-enemy-skills` arm (ANIMREF-R5): an EMPTY
  bar casts nothing **and still swings**, the second half being the control —
  without it the section would pass just as well on an agent that had stopped
  doing anything at all, which is the failure mode the rest of this file exists
  to refuse. Its last section is the one that earned the entry:
  **every combat constant is asserted against a LITERAL written in the test
  file.** That exists because on 2026-08-11 the monster-AI dive sabotaged them
  one at a time and **twelve of fourteen could be set to a wrong value with all
  125 checks green** — `ENEMY_MELEE_RANGE` 150→400, `AGGRO_RANGE` 1200→1100,
  `SWING_WINDUP` 0.899→0.2, all PASS. Only `ENEMY_TURN_RATE` reddened, and it is
  the only constant in the set corroborated to the bit. Not a coverage accident
  but a shape: every other section computed its expectation *from* the symbol
  under test, so the symbol was free to move and the test moved with it. **A
  symbol appearing in a test file is not a check.**

  **And one constant in that registry is now pinned the OTHER way round, on
  purpose.** As of 2026-08-20 the player's swing is no longer a fraction of the
  target's maximum health — it is the equipped weapon's own damage range, read
  out of its **584** modifier word (`arg` the maximum, `arg2` the minimum;
  ArenaNet's renderer draws `Blunt Dmg: 3-5` for our hammer). That number is
  MEASURED rather than ours, so pinning it to a literal here would be the same
  defect from the other side: it would let `content/items.toml` change while the
  test went on agreeing with a range nobody sends. `section_weapon_damage` pins
  it to the WORD instead — it re-reads the item and requires the server's
  constant to match — then rolls **200 swings and requires every one inside
  3–5**, and requires the roll to actually vary, because a range that always
  returns its own minimum is a constant wearing a range's clothes.
  `HIT_FRACTION`'s registry row now says what it is: the fallback for an
  attacker with no readable weapon, and nothing else. The same section reads
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
  the two are identical in shape.
  **Floor 248 against a green 261, MEASURED both ways 2026-08-31** — this entry
  read "floor 214 against a green 223" and both numbers were long stale; the code
  said 256. The floor is now the BARE-MACHINE subset (`test_armour.py`'s
  precedent, `test_quests.py`'s shape), and it could not have been measured
  before that day because a vault-less run of this file never reached a verdict
  at all. It stopped THREE times, each hidden behind the last: (1)
  `handle_skill_press` → `player_rank_for_skill` raised `ContentError` — a SERVER
  defect, fixed there; (2) `pinned.find()` raises **`SystemExit`**, which is
  `BaseException`, so the `except Exception` guarding the skill-table read could
  not catch what it called and the skip it was written for had **never once
  fired** — `test_compositetrap.py` §1 hit exactly this on 2026-08-30 and its
  `except (Exception, SystemExit)` is the shape copied here; (3)
  `probes.check_encodable()` built every probe outside its own try, and nine of
  them bind `def_1480` — the vault NPC row `test_bareimport.py` exists about —
  while their steps are built. Those nine are now SKIPPED and named rather than
  fatal, and the section additionally asserts `counts["checked"] > 0`, because
  **0 failures over 0 steps is what a machine that could build no probe at all
  reports** — the `test_codec.py` fixture-glob shape. One more pairing was found
  on the way: §3's "slot 0 lands NO damage" is only evidence that 276 is a HEAL
  while some other skill on the bar DOES damage, so it and its 312 control now
  skip together — bare, the damage path is inert for every skill and that check
  would otherwise pass for precisely the reason its control exists to rule out.
  Reverting the `SystemExit` catch returns the file to rc=1 with zero verdict
  lines, run rather than assumed. 248 checks, 5 declared skips, rc=0 with no
  vault. **Floor 268 against a bare 268 / green 281 since 2026-09-02
  (ANIMREF-RE §40)**: §chase was REWRITTEN with the new evidence rather than
  deleted when the hostile's chase became retail's follow — 32 checks that pin
  the `0x002A` naming the player in its fifth field, the half-second re-path
  (none standing, none inside 0.5 s, one after it to the player's CURRENT
  position), the server's copy parking at `r + r + 56 = 80 u`, the bare
  `0x0028` halt with nothing riding it, the refusal to swing mid-follow, the
  150 u case that used to swing now walking in, a follow ended by the player's
  death, the wall, and the `--legacy-npc-chase` arm run under the flag (rate,
  facing, `0x0029`, 150). §facing had driven `face_player` through the chase,
  which no longer calls it (retail's 7 live chases carry no `0x002E`), so it now
  drives the function directly with two new pins on the call site: the follow
  announces no facing and the swing open still does. The registry keeps
  `ENEMY_MELEE_RANGE = 150` and `ENEMY_DEST_RESEND = 120` as the LEGACY arm's
  literals, re-worded to say so. **§40.1, same day, on the operator's CASE 8
  capture:** the engage reach had been the player's 144 u press reach borrowed,
  and the Hatcher stood and swung across an 80–144 u band; it is now the halt
  disc plus one radius (92) and §chase pins the deadband at ≤ one radius —
  `_world`'s default distance moved 100 → 85 with it, since 100 sat inside the
  borrow and outside the correction. **§40.9, on CASE 8 v2:** the chase rate is
  1.0 (the registry row is OBSERVED now — 6 of 6 retail chasers) and the halt
  waits for the follow's half-second clock; §chase pins the arrived-not-halted
  state (no `0x0028`, no swing), the halt once the clock is aged, and the
  `--halt-on-arrival` revert arm),
  `toolkit/authsrv/test_interact.py` (the interact path — the walk order and the
  interact that is HELD rather than dropped. **Nothing exercised
  `_handle_interact` at all before 2026-08-19**; `test_dispatch.py` named it once
  in a docstring, so the range gate and every consequence of talking to an NPC
  were carried by no check, and a bug lived in that gap from 2026-08-16. The bug:
  clicking a distant NPC did not move the player, and the recorded diagnosis —
  that the CLIENT walks you over and only our range number was wrong — was wrong
  in both halves. Measured over five keyed live captures: the stock client sends
  **no** movement order of its own on an NPC click (46 interacts, 0 with a
  `0x003E` inside 100 ms), ArenaNet's server sends `0x002A`
  `AGENT_UPDATE_DESTINATION` naming the PLAYER's agent (17 in the corpus, 16
  within one round trip of the interact naming the agent walked to), and it does
  not drop the out-of-range interact — it answers it after about
  `(gap − range) / 288 u/s`, the walk's own duration (1054 u: predicted 2.79 s,
  observed 2.56 s). §1–2 assert the order goes out and carries the corpus's own
  payload (player's agent, the target's position, the target in the follow slot
  `0x0029` hardcodes to zero) and that it frames to the declared 22 B. §3 asserts
  the hold is served on arrival **and only then**, including that a tick with the
  player still distant re-sends nothing — a 20 Hz destination storm no capture
  shows. **§4 is the control that matters**: `_order_walk` must NOT set
  `state["dest"]`, because the server's integrator would then advance our idea of
  the player's position whether or not the client moved, and the hold is gated on
  that position — a client stopped by its own collision would get a dialog opened
  while standing still, the same shape as the 765-unit warp the world tick's
  comment records. A test asserting only "the interact eventually fires" passes
  with that bug in. §5 is the in-range control (served at once, no walk order,
  nothing held) and §6 covers the two ways a hold must not outlive its reason: a
  second interact cancels it, and an agent that leaves the world drops it. Floor
  19, measured — it was written as 18 from a count in the author's head and
  corrected against the run. No vault, no client. ~1 s),
  `toolkit/authsrv/test_poschecksum.py` (**GAME_SMSG 0x0023, ArenaNet's own
  movement-state checksum — and the guard is unusual because the message's
  whole output is a line in the CLIENT'S OWN LOG.** Nothing it does reaches the
  wire, a capture, or any state this repo reads back, so there is no round trip
  to assert: every check is either our builder against the client's own
  arithmetic re-derived from `struct` alone, or a refusal that stops a broken
  probe reporting a comfortable silence. §1 recomputes the five-dword XOR at
  `0x005FEEA0` — velocity `+0xB4`/`+0xB0`, plane `+0x80`, position
  `+0x7C`/`+0x78` — WITHOUT calling the module under test, because a builder
  compared against itself is not a check, and pins that `-0.0` and `0.0` give
  different checksums, which is the whole hazard of a bit-exact compare. **§3
  is the one that matters: it is the positive control's own control.** The
  `wrong` arm exists so the client's line appears at least once, and its value
  is that its prediction cannot come true by accident — so the sentinel is
  asserted non-zero, asserted to change field 2, asserted NOT to touch the
  agent id (which the client indexes the SYNC array with, and a corrupt one
  asserts inside the client at `Array.h:587` instead of logging), and its
  XOR-is-an-involution property is stated so it cannot be applied twice. Were
  the sentinel ever zero, the positive control would silently become the model
  arm and a silent run would read as "we match the client bit-exactly" — the
  strongest claim this arc could make, and false. §4 pins the wire: 10 bytes,
  opcode first, then id, then checksum, because the handler reads `[edi+4]` and
  `[edi+8]` and swapping them indexes an array with a checksum. §5 holds the
  probe OFF by default and requires the model to NAME the assumption it is
  wrong under. **What it deliberately does not claim:** that field 2 is what a
  real server would send — retail sends this opcode 0 times in 137 live capture
  files, so the sender is a RECONSTRUCTION inferred from the client's compare —
  or that the client agrees with us, which needs a client and is what the probe
  run is for. Floor 20, read off a real green run and set AT it, zero headroom.
  No vault, no client. ~1 s),
  `toolkit/authsrv/test_familyrate.py` (REALFIX-A1's family-rate probe --
  **the accuracy campaign's first rung, whose whole verdict lives in an owner
  run this file cannot perform**: whether a wire 0x002B float steers the SYNC
  copy's +0x60. What it CAN refuse to let rot, section by section: §1 the
  CONTESTED FAMILY_RATE table's shape -- domain exactly mt 1..8 (the census
  is 9,463 of 9,463 decoded reports inside that range), forward rows 1.00,
  and the two rows with live single-frame witnesses pinned to them (4 ->
  0.66, CANCELWALK-F4; 8 -> 0.75, found 2026-08-25 in the same capture),
  every value inside the client's own asserted [0.01, 1.0]. §2 the builder
  passes the table through as [player, rate, mt] (the facing byte IS the
  movementType, retail's own encoding) and refuses a units/s 288.0 -- the
  0x0027-confusion the client's assert exists for. §3 the sender: one send
  per known family with the label naming the rung and the readout column,
  and an unknown movementType sends NOTHING and prints ONCE -- driven twice
  with stdout captured, because a bare FAMILY_RATE[mt] would KeyError a live
  connection and a silent skip would let the census go stale unnoticed. §4
  the codec round-trip: the builder's fields encode to the schema's 11 bytes
  and decode back to [43, 1, ~0.66, 4]. §5 the composition cells: refused
  without --zero-lead (the gate is the zero-lead verdict -- inert-flag
  defect otherwise), refused pairwise with --cancel-answer in BOTH its modes
  (the lead arms hardcode a rival [1.0, mt] on the same client field), the
  pairwise cell asserted to OUTRANK requires-zero-lead (the first draft had
  it below and this check went red -- kept as the record), allowed with
  --zero-lead with the note pricing the click-site hazard by its exact
  [1.0, 1] signature, and composing with --resync (different opcode, no
  mechanism for a refusal). §6 source locks, the 2026-08-25 review's
  lesson twice over: the global defaults False and is rebound exactly once,
  ONE gate (`if FAMILY_RATE_PROBE and zero_ok:`) and ONE call site -- and,
  after the probe's own review showed two mutations surviving the string
  counts, the gate's POSITION is pinned by src.index ordering (strictly
  between the 0x0025 send and the first grant block -- relocated below the
  0x0029 every count stays green while the wire shows a shape retail never
  produced) and the call's mt OPERAND is pinned verbatim (hardcoded, every
  send becomes [1.0, 1], the exact click-confound signature, and no count
  reddens). §7 the checksum pairwise cell, the same review's burst-purity
  find: --checksum-probe had never been in the composition matrix (correct
  for its own solo runs -- the handler logs and returns 1), so the pair ran
  unrefused with an 0x0023 riding the probe's burst; now refused pairwise,
  while checksum alone stays unrefused. Floor 26, read off a real green
  run -- the first draft declared 26 from a head-count, the ledger went red
  on the 22 that ran, and the review's added checks landed the measured
  count back on 26 by coincidence; the history is in the floor comment.
  No vault, no client. ~1 s),
  `toolkit/authsrv/test_pcspoof.py` (REALFIX §0.7 cell 2's lever, --pc-spoof --
  **the parked+`pc`-flip cell the owner could not stage by geography** (the
  plane seam is a bridge too narrow to strafe, run of 2026-08-25 ~23:17), so
  the flip became a server decision: the first fired zero-lead grant after
  ≥4.0 s of grant silence sends the flag's plane id as wire field 4, once per
  park. The cell's verdict -- does the flip snap a PARKED copy? -- lives in an
  owner run this file cannot perform; both outcomes are registered (§0.7: NO
  snap predicted; a snap means gate 2 is plane-keyed). What it CAN refuse to
  let rot: §1 the pure trigger's truth table -- off is a pass-through, first
  grant (since_last None) spoofs, the ≥ boundary at PC_SPOOF_GAP exactly, leg
  cadence is safe (the A1 tape's own 3.054 s maximum gap asserted NOT to
  spoof, because the constant is sized off that measurement), int coercion,
  and plane 0 spoofable (an `if spoof:` truthiness bug would exempt the one
  plane every map uses). §2 the composition cells: refused without
  --zero-lead (no send site, no gap clock -- the inert-flag defect), refused
  negative (not a plane), refused pairwise with --cancel-answer (the lead
  arms ride the SAME 0x0029 send whose field 4 the spoof rewrites), the
  pairwise cell asserted to OUTRANK requires-zero-lead per the family-rate
  precedent, allowed in its registered shape with the note naming the armed
  value and the ground-plane-void warning, and allowed beside
  --family-rate-probe (different wire fields). §3 source locks: exactly ONE
  rebind site routes zl_plane_cur through the helper, its POSITION pinned by
  src.index ordering strictly between the arrival-carry assignment and the
  send path's own grant_verdict row (the verdict anchor searched FROM the
  rebind, because its first file-wide occurrence is matrix prose at ~:5299 --
  above the carries the carry would silently overwrite the spoof; below the
  verdict the row would log a value the wire did not carry), the row's
  pc_spoofed census key, the PC-SPOOF wire-label marker, and the send site
  still reading field 4 from zl_plane_cur verbatim (the lever works by
  REBINDING that name -- an independent field-4 expression at the send would
  strand it inert while every count stayed green). Floor 23, read off the
  real green run -- the first draft declared 21 from a head-count and the
  run said 23; the history is in the floor comment. No vault, no client.
  ~1 s),
  **§2e is MOVECODE-1z-ap, THE PLANE-BLIND CLIP** (FINDINGS §1z-ap): `pm.walkable()`
  means *"inside any trapezoid, on ANY plane"*, so `a2_clip_lead`'s ray from a bridge
  to the ground beneath it scored CLEAR at full length — there is NO HEIGHT in the
  pathing file, and a plane-29 and a plane-0 trapezoid can occupy the same (x, y) with
  no straight walk between them. RUN-1zAO measured the cost in the client's own memory:
  the lead `(10373,8286) → (9853,8286)` passed at 520 u, the drawn body did not move for
  3.0 s under a held key, separation crossed gate 1 and reached 502 u, and the arrival
  warped the body 520 u and shut AgTrack's fence permanently. The section drives **the
  KNOWN-BAD ARM FIRST** — with `--no-lead-plane-clip` the seam ray goes out at full
  length reading `clear`, so the shipped cell is known to be measuring the plane term
  and not the wall — then the shipped arm stopping AT the seam with the row **naming
  the door** (`why="plane-seam"`, not `"clipped"`, because the two have different fixes
  and this file already paid once for a clip whose row did not say which had opened),
  and the surviving reach being under gate 1's 299.33 u so the granted point cannot be
  the far side of a snap. Then the three ways it must NOT fire: a same-plane clear ray
  is **bit-identical on both arms** (a clip that perturbs healthy grants by epsilon
  rewrites every one of them); a ray into the wall still reads `clipped`; and a mesh
  that cannot NAME the origin's plane — `plane_at` returning None, "say nothing, never
  a guess" — **disables the term rather than guessing a surface**, as this file's own
  no-mesh door already does. A pathmap with no `plane_at` at all keeps the historical
  answer exactly, and the `plane=` kwarg is passed only when the term is in force, so a
  stub or an older mesh object cannot raise inside the recv loop. Plus the flag cells:
  ships ON, `--no-lead-plane-clip` the one revert, bound from argv, and the ray's plane
  taken from `plane_at(prefer=` the REPORT's own plane word rather than `state["pos"]`
  or a literal (`--heading-grant`'s graveyard). 94 → **104 checks, floor 104**, set from
  the green run. **§2f (2026-09-04, MOVECODE-1z-bc) is the SEAM VARIANT of that clip,
  OPT-IN AND REFUTED AS A DEFAULT.** `pathmap.seam_clip` — the router's primitive since
  1z-bb, a plane may end only at a portal — was built to replace §2e's any-plane-change
  stop and let a lead through a bridge's end ramp; `studies/movecode/review/leadretro.py`
  replayed the lead campaign's 622 leads through both and found every one of the six
  fatal leads of the six measured locks going out at the full 520 u under it (0 of 6
  kept under gate 1), because at both ends of the spawn-side bridge the seam the body
  would not walk is portal-linked in the file. So the section pins the DEFAULT — a ray
  through a file-linked portal is still cut at the plane change — as the shipped cell,
  the opt-in arm (`--lead-seam-clip`) granting that same ray at full length, the blind
  side-exit still stopping under either arm with its reach under gate 1, a mesh without
  `seam_clip` falling back to the plane clip unchanged, and the source: ships OFF, the
  flag is opt-in and bound from argv, the lead reaches `seam_clip` at exactly one site,
  and the file records WHY the default is off (the 0-of-6 number is a substring lock,
  so a later reader flipping the default has to delete the reason first). 104 → **110
  checks, floor 110**.
  `toolkit/authsrv/test_d1lead.py` (REALFIX-A2's `--d1-lead` bundle, and since
  2026-09-01 also **§R11: the grant-during-hold A/B lever.** SHIPPED suppressing and
  REFUTED by the very next run -- the default is back to granting and the suppression
  is now opt-in (`--suppress-grant-during-hold`). It removed the body relocation it
  targeted and took the SLIDE with it (recovery lag p50 62 ms -> 406 ms, dispatches
  333 -> 59, owner score 1 -> 0), because the slide WAS the grant (FINDINGS §27).
  ANIMREF FINDINGS §26 caught the whole chain in one movehook record, twice: a
  press the client REFUSED at its walk gate still emits a `0x003D` (§22.2), our
  server answers it with a destination grant, and the client applies that grant
  through AgTrack's roster walk (`0x00604880`) as a `setposition` -- RELOCATING
  the displayed body while the player's own walker pulls the other way. The
  discriminator has its control: of grants FOLLOWING a refusal 2 of 15 relocated
  the body, of grants not following one **0 of 29** did; and retail suppresses
  10:1 in the same state (0.050 grants/s held against 0.519/s clear -- a RATE,
  because the windows differ in length and that denominator already cost this
  arc one reverted fix). Four structure checks (default False, exactly one
  guarded send site, the suppression PRINTS rather than going silent, the revert
  flag exists and binds), a two-arm predicate check whose **known-bad arm must
  score badly**, and an audit lock that the guard opens BEFORE the plane advance,
  the leg arm and the arrival carry -- because R11's own first cut guarded only
  the send, which would have left a suppressed grant arming a leg whose ETA the
  watchdog then re-pins: the relocation R11 exists to prevent, reintroduced one
  line below the fix -- `--legacy-grant-during-hold` restores the relocation, and
  a guard that passed in both arms would be measuring the wrong quantity. It is
  a source-and-predicate check rather than a wire drive because the send lives
  inside `handle()`, the socket handler, with no seam to drive it through -- **the
  accuracy campaign's lead rung, whose whole verdict lives in an owner run
  this file cannot perform** (the registered predictions P-1..P-5 and the
  REFUTED-IF lines are REALFIX.md §0.9 and the startup banner; P-1 is the
  C1-warp-recipe A/B, zero snaps against a 4/4 baseline). What it CAN refuse
  to let rot, section by section: §1 `d1_lead_dest`'s formula exactness --
  the +0.5·unit term whole on an axis AND on a diagonal (a wrong
  normalization reads plausibly axis-aligned and only the diagonal catches
  it), and the refuse-don't-clamp fallback: zero/tiny/over-ceiling
  (769.0 inclusive, measured max 768.0 plus slack)/NaN/malformed vec2 all
  fall back to the zero-lead point rather than clamping or raising (a
  TypeError in the connection handler kills the session for one bad
  report). §2 the family edge's whole truth table: first family sends under
  the A2 label (not the A1 probe label -- the unattributable-capture
  defect), same family holds, change sends, an unknown mt loud-skips
  WITHOUT advancing the edge, and the stop-reset (`a2_family_sent = None`)
  re-sends the SAME family -- the one transition the A1 probe never needed,
  because the stop-ack's [1.0, 9] overwrites sync +0x60. §3 the lattice:
  seven pairwise refusals (cancel-answer, family-rate-probe,
  checksum-probe, pc-spoof, stop-answer, arrival-carry -- reachable only
  with plane-carry off, since the older plane-vs-arrival cell correctly
  preempts it otherwise -- and click-sweep), the two requires cells
  (zero-lead, plane-carry), pairwise-outranks-requires per the family-rate
  precedent, and the allowed shape's note naming the bundle and the
  stop-repin's era-audit ground. §4 source locks, position-pinned per the
  house pattern: the global/rebind/threading triple; ONE speed-truth gate
  (`if D1_LEAD and zero_ok:`) sitting in the witnessed burst slot AFTER
  the A1 gate and BEFORE `if HEADING_GRANT:`; the edge call's mt operand
  verbatim; ONE dest-computation site ordered after the pc-spoof rebind
  and before the verdict row (so the row records the point that goes out);
  the row's `lead_src` key; the ONE 0x0029 send consuming `a2_dest`
  through `zl_point` with field 4 still `zl_plane_cur` verbatim; and the
  stop-repin -- one site, one [a2-stop] speed send, positioned between
  CANCEL_STOP's scoped re-pin and R6's bare ack inside the 0x0047 handler,
  with the family-edge reset inside its own block AND its two sends'
  ORDER pinned (0x002B before the 0x0029 -- the build review's one
  surviving mutation, MUT-7, now caught; retail's stop grammar is 131/131
  companion-first). The d1 band is [700, 769] with both edges pinned and
  the corpus's one mid-magnitude outlier (|v|=1.997) asserted to fall
  back -- the review's MINOR. The §0.11 armer-kill (matched plane words under
  the bundle: `a2_matched_field4`, field 4 always matches field 3 -- retail's
  222/222 -- so the stale-carry seam state that shut the AgTrack fence and
  locked the owner's input can never exist) adds its truth table plus four
  locks: def + exactly TWO call sites (heading arm and stop-repin), the
  heading-arm override ordered carry/spoof → override → dest-compute →
  verdict row, the row's `pc_matched` verification key, and the repin
  label's "matched" marker (the stale word was the lock's 28/28 detector --
  the marker keeps its trace under the fix). The §0.12 containment pair adds
  §2b's truth tables -- the leg model (a2_leg_note records the FAMILY speed,
  a2_leg_position interpolates at it and CLAMPS at the dest: the incident's
  recovery-click case) and the watchdog's five-clause due-predicate (no-leg /
  pre-ETA at the 190.08 u/s floor speed so it can only be late / eta-passed /
  click-in-flight stands it down / once per leg) -- plus site locks: the leg's
  three pops (two discards where the client spoke, the click arm's CAPTURE),
  ONE arming site in the post-send bookkeeping, ONE watchdog call site gated
  D1-and-game-channel on the recv loop's quiet ticks with its one speed send
  and one matched repin, and the click arm's placement AND clip both reading
  the model-or-reported position through one computation site (a half-fixed
  placement read would place the player at the leg's START -- the exact
  staleness being corrected). The matched-words census went 3→4 appearances
  (the watchdog's repin is the third caller). The containment review's fixes
  add four more pins: the REV-1 None-latch regression cell (the one REAL --
  the watchdog's click clause would have crashed the session on a
  present-but-None `click_moving_at`; `or 0.0`, not a .get default), the
  MUT-1 floor-value pin plus a 20 ms ETA-boundary bracket (768/190.08+1.0 =
  t0+5.0404 s -- a 288-flat floor flips both cells), the MUT-7 `a2_src ==
  "d1"` arming-guard lock (phantom legs on fallback grants otherwise), and
  REV-2's read-not-pop capture lock (a popped leg answers only the FIRST of
  a double-click). The §0.13 F-B click contract adds §2c's rate-gate truth
  table (`a2_click_rate_ok`: the shared clock alone gates clicks under the
  bundle, ≥-boundary at the floor, and missing-OR-None `grant_at` reads as
  ancient without raising — the REV-1 lesson generalized) plus five locks:
  the matched-words census 4→6 (both click-answer sites now match), the
  family-re-arm census at 4 (all four `[1.0]`-overwriting sends), BOTH
  Rule-1 bypass sites rewriting to the additive `d1-click` reason, the
  immediate bypass ordered ABOVE the verdict row (the row records what
  happened), and the geometry branch's new `click_verdict` row with its
  `d1_passthrough` marker (the soak's 138 no-trace clicks). The F-B review's
  fixes add four more: the grantsim C3 skip for `arm=click-d1` rows (REV-1 --
  the first draft's own lock text called the filters "untouched" as a virtue;
  untouched was the defect, and the check now tells that story), both click
  rows naming their policy with the `deferred-d1-click` marker preserved
  (REV-4), and the flush's three call sites with the world-tick one gated
  OFF under the bundle (REV-2's cross-thread clock race -- recv-thread-only
  sending, pre-batch ordering giving held clicks first claim on each floor:
  REV-3's starvation closed by the same move). §0.14's F-A supersedes F-B's
  immediate mid-keyboard answer (its premise refuted: retail never
  verbatim-echoes DISTANT mid-keyboard clicks; 21 through-geometry snaps,
  20/21 grant-edge-triggered): the locks now assert the immediate bypass is
  GONE (count 0, the check telling its own inversion story), `click-held` at
  one site ordered above the verdict row, the eager void at one site gated
  on the report being ACCEPTED (a rejected report must not cancel the
  player's click), and the flush's `d1-click` fire remaining as the ONLY
  answer path for release-clicks. §0.15 then DELETED both click rewrites and
  their rate gate (each refuted within the day — F-B's immediate answers
  raced the copy through props, F-A's flush fires were the direction-yank
  engine at 35/44 sharp turns) and the checks INVERTED to assert the
  absences: no rewrite strings at either site, a2_click_rate_ok gone as an
  attribute (a helper with no callers coming back means the resurrection
  path re-opened un-litigated), and the gap between _grant_verdict and its
  row EMPTY (both refuted rewrites lived exactly there and each made the
  row lie). Added: the outstanding-answer hold's three locks (the stamp at
  both click send sites, the or-0.0 read at one flush site BEFORE the
  verdict call — the double-click stomp fix). §0.17 completes the pair and
  half-closes Q7: the gap lock EVOLVES from empty-gap to refuse-only-hold
  (exactly ONE rewrite permitted in the gap, the literal `may_grant, why_g
  = False, "answer-outstanding"` — refuse-only, never the graveyard's True
  direction — with the LEG BOUND separately pinned: `state.get("dest") is
  not None`, because the flush's bare predicate at this site is a SILENCE
  detector that the 113833 offline counterfactual showed suppressing 22 of
  24 real staircase fires), the outstanding-stamp read census goes 1→2
  (both hold sites), and the D2 lead clip lands with §2d's four pure cells
  (a blocked-band ray clipped to the NEAR side — the wall-phase cell
  itself, where walkable(dest) alone would pass it; a clear ray untouched
  bit-exact; the no-mesh and off-mesh-origin doors mirroring
  clip_to_walkable's) plus four locks: def + ONE call site anchored on
  `reported` verbatim (R2-1's graveyard), ordered dest-compute → clip →
  verdict row, the row's `lead_clipped` census key, and A2_LEAD_CLIP_STEP
  pinned at 2.0 < COLLISION_STEP (the Q7 desk check reproduced retail's
  world-anchored clip coordinates on our own mesh only at a fine step).
  Floor 81 re-measured (72 → 80 with the pair, 81 with the leg-bound pin);
  `test_grantsim.py` green at 86 beside it. §0.19 (the RETHINK instrument-#1
  build, logging only, zero policy deltas) extends the 2d cells to the
  clip's new `(dest, clipped, why)` arity — the four why strings each
  pinned, `origin-unwalkable` carrying the P-17 escape-door story — and
  adds five row locks: `lead_clip_why` on the lead row (with the
  `fallback` branch), the FLUSH hold's refusal row (once per held item,
  latched by `hold_logged` — the one guard branch that had no row, whose
  inertness the P-17 decode had to prove by absence), `kbd_age` on every
  position_report row (or-None discipline), the `a2_leg` lifecycle (ONE
  arm site, TWO clears riding the same pops the read-not-pop lock pins),
  and the watchdog-due reason-TRANSITION row. Floor 86 re-measured.
  Landing note: this test's arrival forced two deliberate
  lock extensions in the same commit -- test_familyrate §6's sender census
  went 2→3 appearances (the def, A1's call, A2's edge-wrapper call; the
  matrix refuses the two flags together so at most one is live), and
  test_position_trust's AST lock on `zl_point`'s permitted values went red
  the moment the A2 edit landed (the lock working) and now admits exactly
  the audited IfExp whose else-branch is still `list(reported)`. No vault,
  no client. ~1 s),
  `toolkit/authsrv/test_kbdsync.py` (**MOVECODE-1z-t, the keyboard world-0
  sync — the behaviour that ships by default from 2026-09-03.** The defect it
  answers was measured in the client's own memory, not inferred:
  `agenttap.py` records BOTH world copies, and on the 2026-09-02 kite the
  player's world-0 copy sits a median **237 u** from the world-1 copy that is
  DRAWN, against retail's ~74 u — which is the whole of ANIMREF-RE §40.11's
  enemy-swing symptom, since the collision disc parks the enemy relative to
  world-0. The cause is one sentence of binary: `0x0029` is SYNC-ONLY and
  `0x0025`'s setter writes only the facing triple, so a fresh `0x0029` is the
  ONLY thing that moves world-0, and the bake `0x005FE950` arms a FIXED
  `|v| = maxSpeed × moveSpeed` toward it — so granting the point the body has
  already left leaves the copy parked behind by `report_gap × speed`
  (1.80 s × 288 = 518.4 u predicted, **516.1 u measured**; retail's
  0.257 s × 288 = 74.0 u, cadence ratio 7.00× against separation ratio
  6.97×). Three terms, default ON, `--legacy-kbd-sync` reverting all three
  and `--no-kbd-lead` / `--no-kbd-speed-truth` / `--no-kbd-stop-echo`
  reverting one each — because shipping three defaults into one run convicts
  the trio and clears none. **The verdict is an operator run this file cannot
  perform** (`agenttap.py --agents 1`; the registered prediction and its
  REFUTED-IF are §9 here and the startup banner). What it CAN refuse to let
  rot: §1 the constants and their derivations — 520 u is the client's own
  `0x003D` distance trigger (held-heading chord p95 513.8 / p99 515.1 u),
  read off the client rather than fitted, and the fact that it must exceed
  one grant-interval of travel; §2 that the lead's LENGTH is ours and its
  DIRECTION is the client's — pinned on an axis AND on a diagonal AND at both
  ends of the band, which is the whole difference from `d1_lead_dest`, whose
  lead is the client's own 766 u endpoint (a lead that silently inherited the
  vec2's magnitude would be D1 with extra steps and only the diagonal catches
  it); §3 refuse-don't-clamp over six malformed vec2 shapes, with the band
  REUSED from `d1_lead_dest` rather than restated so the two cannot drift;
  §4 the composition — with `--d1-lead` also set the wire carries D1's
  endpoint and NOT 1z-t's, so a `--d1-lead` run still measures REALFIX-A2 and
  not a mixture; §5 the wire term by term plus the burst ORDER
  (`0x0025` → `0x002B` → `0x0029`, the grant last — retail's grammar, 3,023
  of 3,071 live bursts with zero counter-examples; out of order the client
  bakes the leg before the family rate reaches `+0x60`); §6 each term
  reverting alone, including that `--legacy-kbd-sync` is byte-identical to
  the pre-1z-t server (if it is not, the run that convicts 1z-t has no
  control); §8 source locks — ONE dest-computation site, the branch ordered
  above the verdict row so the row records the point that goes out, the clip
  gated on a REAL lead, the flags rebound through ONE declared `global`, and
  the three `[1.0, 9]` senders distinguished by their bracket tags rather
  than by a string count (a bare count reads 3, not 2, because the ETA
  watchdog is the third sender — the lock would have failed for a reason
  unrelated to what it guards). The stop echo's own wire shape is pinned in
  `test_position_trust` instead, in "THE STOP ARM, BOTH REGIMES", because
  that is where the arm it replaces was pinned: that check used to read
  "with `--zero-lead` ON a `0x0047` grants NOTHING" on the ground that a
  stop-arm `0x0029` IS `--stop-echo` and `--stop-echo` is REFUTED, and it is
  now re-aimed rather than removed — the epitaph's own 2026-08-25 correction
  says the refutation is of **baking a long leg from a far copy** (~1,286 u
  in 2026-08-19, against ~60 u p50 for retail's own stop-ack, "MECHANICALLY
  THE SAME MESSAGE"), which is a precondition term 1 supplies. It now checks
  three things instead of one: the legacy wire still grants nothing, the
  default sends retail's stop reply in retail's order, and NEITHER regime
  ever sends `0x0028` on a stop. Imports `receive_arm`/`Sent`/`FakeRec` from
  `test_position_trust` rather than copying them, because two copies of a
  subtle source-extractor drifting apart is a failure this repo has already
  recorded. **Sections 10–11 (2026-09-03 night, MOVECODE-1z-y) added 27:** a
  report refused `heading-rate` is HELD with the grant the arm had computed
  (the lead its own heading names, plane words as computed), kept inside the
  floor and fired at it with a `deferred-heading` row, the keyboard leg record
  and the plane-slot advance; newest wins; a fired report clears; zero-lead
  holds the report itself; expiry, a stopped body and R11's action hold each
  drop with their row; the known-bad arm `--no-kbd-hold` drops and sends nothing
  (the 08:46 shape); a fired lead arms `kbd_leg`; the kill 1.0 s into a 520 u
  lead grants the modelled body 288 u along the heading on its own plane, consumes
  the record and rows the unwalked 232 u; a matured lead is not re-granted; no
  leg, no send; `--no-kbd-lead-kill` arms nothing and leaves an armed record
  alone; and the kill's source is a `0x0029`, never a `0x002C` (Clear closes the
  fence). Six source locks: the press and click call sites, the three poll sites
  beside the held click, the hold stored between the verdict row and the fire,
  the leg armed at the fire site and popped by both report arms, the stop arm's
  clear. **Section 12 (MOVECODE-1z-z, same night) added nine:** the matched plane
  word on the KBD lead grant ships ON with its revert; a crossing lead (report
  plane 29 over a carried 0) goes out dest 29 / cur 29 with `pc_matched` TRUE on
  its row; the known-bad arm `--no-kbd-matched-plane` sends dest 29 / cur 0 (the
  073121 12.358 s shape); a same-plane lead records the override as not fired; a
  refused crossing re-aim is HELD with the matched word; the zero-lead default's
  F1 lag is pinned UNCHANGED (scoped out, stated); the stop echo's two words are
  the report's plane by construction; and the match sits inside the KBD lead
  branch before the lead point. **Section 13 (MOVECODE-1z-aa, same night) added
  fifteen — the fence-shutter audit's gate:** the tracker is stamped by a player
  `0x002C` and by neither a grant nor an NPC placement; a lead computed mid-walk
  under a fence we shut degrades to the zero-lead point with `lead_clip_why`
  `fence-shut` and arms no record; a walk-start report (moving, latch clear)
  re-arms it with a `fence` row and the lead of that report fires; the held re-aim
  stores the degraded point; the D1 lead degrades the same way; the known-bad arm
  `--no-kbd-lead-fence-gate` sends the 520 u lead into the shut fence; and four
  source locks (stamped once in the send choke, cleared in one place, the stop arm
  untouched, both branches through the gate). §14 is MOVECODE-1z-ae, REFRESH
  BEFORE MATURATION: the lead's own arrival is a sec.0.11 stage-1 armer (the client
  snaps to the granted point when `+0x48` fires), so at ETA minus two ticks the leg's
  destination is pushed a lead further along the ray it is already on. It drives the
  due/not-due edges, the extension's geometry and matched words, the arrival moving a
  full leg out, **the record keeping its origin and t0** so the ray stays anchored on
  the client's own report and `a2_leg_position` is continuous across the refresh (the
  first draft aimed from the model and `test_d1lead`'s clip census caught it), the
  one-per-report budget and its reset, the refusals on a reported stop and a shut
  fence, `refresh-late` once when the arrival wins anyway, `refresh-blocked` when the
  clip refuses the extension, the known-bad arm, inertness with the lead off, and
  four source locks -- and the flag it drives is OPT-IN and OFF since 1z-af, which
  convicted the backstop on two runs that both locked (one past a `refresh-late`),
  so the section's first check pins the default OFF rather than ON. **Section 15
  (MOVECODE-1z-bw) added eight:** the fence latch is BOUNDED at 8.0 s, above the
  client's own measured maximum shut (6.087 s), with `--no-fence-latch-timeout`
  kept as the exercised known-bad arm. **Section 16 (MOVECODE-1z-cc) added
  twenty-one, and it is about the one leg in this file that never touches the
  wire:** `state["dest"]`, the server's own model of where the player is walking,
  which the world tick integrates into `state["pos"]` and which the NPC follow,
  the leash and every range check then read. Two terms, ON, each reverting alone
  (`--no-model-plane-clip`, `--no-model-leg-bound`). The fixture is a SEAM and not
  a wall -- everything in it is walkable, so a plane-blind clip runs the ray to its
  end and only the plane term can stop it, which is what makes the known-bad arm
  informative instead of decorative -- and its `clip` is `PathingMap.clip` itself
  bound to that geometry rather than a second copy of the walk. It drives the plane
  term at the primitive (stop at the seam / full 900 u through it on the revert /
  the term can only shorten / the `hasattr` door for a mesh predating it), the leg
  bound as the pure function it is over all six of its named doors including
  `lead-clear` and the refused-report case where the two legs' origins genuinely
  differ, then joins both ends through the REAL receive arm on RUN-NPCTRACK-R1's
  own geometry: the grant is byte-identical on all four arms, the known-bad arm
  walks the model 766 u through a seam its own grant stopped at, and EACH term
  closes it ALONE -- two independent conjuncts, so a run that reddens one localises
  the change. The last two checks are the regression it must not cause: on open
  ground the model keeps the client's own 766 u ray against the lead's derived 520,
  because that 248 u is the margin over the client's own report trigger and capping
  it would park the model mid-cruise. **Section 17 (MOVECODE-1z-cd) added nine,
  and it ships a REFUTATION rather than a knob:** NPCTRACK's wall case asked the
  keyboard lead to refuse a grant whose plane differs from the mover's, and that
  precondition is false 240 times out of 240 -- `pm.clip`'s plane term only ever
  returns a sample it has ALREADY tested on the given plane, so a plane-aware clip
  cannot land off it, and at the specimen the grant is on plane 0 one 2 u sample
  short of the seam with a same-plane route to it. What ships instead is the
  INVARIANT that made the guard vacuous, held in the places where losing it would
  be invisible -- §16's whole lesson being that the same keyword sat in one of
  this file's two clippers for two days undetected. Over §16's seam fixture it
  pins the granted point's plane at the primitive, on the wire through the real
  receive arm, and through `kbd_lead_refresh_tick` (this file's OTHER lead-sending
  site -- one of two sites is exactly how §16's defect happened), plus the check
  no length test would make: the grant's plane WORDS are the mover's and are not
  computed from the destination, so with `--no-lead-plane-clip` the message is not
  merely long but internally inconsistent, saying plane 0 about a point on plane
  29. The known-bad arm reddens all three, and the last check pins the regression
  it must not cause -- aimed away from the seam the lead is still clear at its full
  520 u. The corpus half is `studies/movecode/review/leadplane.py --check`, which
  carries a CEILING OF ZERO on cross-plane grants under the shipped arm and a FLOOR
  on what the same detector must still find in the captures recorded before the
  term shipped -- without that positive control the zero would be
  indistinguishable from a broken census. Floor 33 → 60 → 69 → 84 → 106 → 114 →
  135 → 144 from the
  green runs. **Section 18 (MOVECODE-1z-ce, 2026-09-06): the WALL SLIDE**, through
  `a2_clip_lead` and the real receive arm on a real `PathingMap` square: a report on
  the square's right side heading north-east -- the ray blocked at its first 2 u
  sample, RUN-GROUNDZ-R3's stair climb in miniature -- is granted the side's next
  vertex with `why="wall-slide"`; the known-bad arm (`--no-lead-wall-slide`) gives
  the report back, the zero lead R3 sent 15 times; a HEAD-ON press stays a zero lead
  (RUN-1zBR unchanged); a ray aimed away from the wall is clipped 100 u out as before
  and never consults the slide; the other slide direction; the cap at `KBD_SYNC_LEAD`;
  the wire (`0x0029` names the vertex on plane 0, the verdict row says wall-slide on a
  kbd lead); and the switch in the capture header. Floor 144 → 153 from the green
  run. **Section 19 (MOVECODE-1z-cf, 2026-09-07): the MODEL'S sliver door and wall slide** —
  `clip_to_walkable` from a report 0.05 u outside the square's side (the edge class the client
  slides in) gives the wall's next vertex, not the raw 766 u heading (the known-bad arm,
  `--model-origin-exact`, gives the heading: RUN-FEEL2's phantom the follow aimed at); an inside
  origin slides to the same vertex; a head-on press stands; `--no-model-wall-slide` stands; a
  heading away from the wall is clipped normally; 50 u off the mesh still suspends collision;
  the receive arm writes the vertex as both the model leg and the lead; both switches in the
  header. Floor 153 → 162 from the green run. **Sections 20-21 (MOVECODE-1z-cg, 2026-09-07):
  the lead's two doors, one per link of the owner's own fall-through snap.** §20, the DISC
  (`A2_LEAD_DISC_CLEAR`): on a 2000 u square a lead ending 20 u from a hostile is pushed along
  its ray to one radius past the disc (x = 692, `why=clear+disc-past`); a hostile 680 u off the
  dest changes nothing; a corpse holds no disc; the known-bad arm (`--no-lead-disc-clear`) ends
  inside; where the mesh cannot carry the lead past, it ends one radius SHORT
  (`clipped+disc-short`); header. §21, the ORIGIN (`A2_LEAD_W0_ORIGIN`) on a stub mesh with a
  hole and a stub guard holding the mirror's world-0: a lead clear from the report whose leg from
  world-0 crosses the hole becomes the corridor's first vertex from world-0
  (`clear+w0-route`); a world-0 whose leg holds changes nothing; no guard (a bare machine) skips
  the door; a world-0 already off the mesh is left alone; the known-bad arm
  (`--no-lead-w0-origin`) sends the clear-from-the-report lead; no route gives the leg's last
  on-mesh point (`clear+w0-clip`); header. Floor 162 → 176 from the green run. **MOVECODE-1z-ci (2026-09-07), four checks in the fence-gate section:** a moving report ON the pin point keeps the latch (the harness's held key, whose fence stays shut ~3 s), the same report 100 u OFF the pin re-arms it (`by=walked-off-pin`) and the report's own lead fires, the known-bad arm (`--no-fence-rearm-moved`) keeps the latch, and the constant/flag/header pin; the source lock on the clear count now reads TWO (both in the `0x003D` arm, none in the stop arm). Floor 176 → 180 from the green run. **MOVECODE-1z-cj (2026-09-07):** 21h, a corridor vertex inside a hostile's disc is skipped (F14 halts world-0 there) for the leg's last on-mesh point; §22, the client's OWN reseed read off the report — a report 400 u off the model landing on the mirror's world-0 stamps the latch with itself as the pin (`by=client-reseed`) and its lead degrades; the same jump NOT onto world-0 is a walk (no stamp); no jump, no stamp; the known-bad arm (`--no-client-reseed-latch`) leads into the window; thresholds/flag/header. The `_Guard` stub answers the guard's hooks with no-ops so the report path cannot disable it mid-check. Floor 180 → 187 from the green run. **MOVECODE-1z-cl (2026-09-07):** 21i, door B never names the vertex world-0 already stands on (a 0 u lead that cost a whole heading floor in RUN-1zCG session 4); §23 `a2_lead_words`, the lead's two plane words are the mesh's at the two points — a ground vertex named by a report on the stairs with world-0 on the ground → (0, 0), a stairs destination with world-0 on the ground → (29, 0) (retail's crossing pair), both on the stairs → (29, 29), no mesh / no mirror → the caller's words (the raw-carry arm stays measurable), the known-bad arm (`--no-lead-plane-words`) → (29, 29), and the flag/header/four-caller census; §24 `kbd_lead_chain_tick`, a door-B lead chains to the next vertex at the copy's arrival — the send, the leg advanced with its origin kept; refused while the copy walks, under a shut fence, on a lead the doors did not move; no progress stops the chain once (`chain-stop`); the known-bad arm (`--no-kbd-lead-chain`); polled at all three tick sites after the refresh. The `_Hole` stub gained `containing()` because the chain's send runs through the real choke. Floor 187 → 201 from the green run. No vault, no
  client. ~2 s),
  `toolkit/authsrv/test_livewire.py` (the committed retail-decode recipe,
  RETHINK instrument #2 — the campaign's referee moved out of a deletable
  scratchpad. Guards `toolkit/authsrv/livewire.py`: the no-vault doors
  (missing dir → empty list; no wire.jsonl → origin None, never a default
  to either origin), the LIVE-origin gate passing ≥20 captures while
  excluding at least one non-live directory (a gate that passes everything
  is not a gate), and — the module's whole reason to exist — a NUMBER WITH
  INDEPENDENT PROVENANCE: the 62994 connection's 432 s2c `0x0029` rows,
  counted by the 2026-08-26 drawing-board skeptic's own script before this
  module existed, reproduced exactly by the committed recipe, alongside
  its 12 clicks / 99 heading reports / 2821 total / time-ordering, and the
  rung-7 capture's 8 game connections ALL decoding with full byte closure
  (a partial decode reported as full is the suite's oldest defect class).
  Vault sections skip loudly on a bare machine. Floor 12 from the green
  run. ~50 s),
  `toolkit/authsrv/test_keepalive.py` (**MOVECODE-K1's keep-alive re-grant, and
  the file is mostly REFUSALS on purpose.** `--keepalive-grant` is the *sixth*
  candidate in a family that killed five, and the graveyard at `HEADING_GRANT` /
  `CLIENT_ENDPOINT` is specific about how they died: `--heading-grant` refreshed
  FASTER than retail (0.32 s against 0.49 s) and still warped, because it
  computed its point from `state["pos"]` — the server's own integrated model —
  rather than the report in hand, and because it CLIPPED that point to our
  navmesh where the client's own collision disagrees; `--client-endpoint` met
  both terms it was designed for and warped MORE. So the interesting content of
  this flag is not that it grants, it is **what it refuses to send and where the
  point comes from**, and §5–§7 are therefore SOURCE checks over the world-tick
  call site rather than behaviour checks over the verdict. A future edit
  swapping `client_pos` for `pos` would keep every behaviour test green while
  reintroducing a measured warp — the same shape `test_movehook.py` §11 exists
  for. Both source guards were proven to go red by planting the exact
  regressions: `client_pos → pos` reddens §5 twice, and the clock swap reddens
  §7 twice. **§7 is the clock check and the bug was real during development**:
  `world_tick` runs on `time.perf_counter()` (an arbitrary epoch, for the tick
  delta) while every stamp the verdict reads — `grant_at`, `sync_at`,
  `pos_seen` — is `time.time()`; mixing them does not raise, it makes every
  interval a nonsense number and parks `_sync_position` instantly, so the pin
  gate would read "parked" forever and the flag would grant on every tick. §7
  also pins that the block runs **before** the tick's `dest` early-out, because
  run 5's two real warps both had the player standing still with the twin parked
  hundreds of units away and an early-out on `dest` would skip exactly those.
  §2's fixture starts in a GRANTING state and each test turns exactly one thing
  off — a fixture that started refusing would let a rule stop working unnoticed.
  §4 pins which side of the 100.0 band the boundary falls on from both
  directions, and that the band is the figure `PLAN.md` §7 Q11 already
  reconciled `RESYNC_SEPARATION` to rather than a second constant for the same
  quantity. §8 requires `--keepalive-separation` to REFUSE on its own, because a
  run launched with only the override would look configured and change nothing.
  Every section is process-free, so floor 32 is the whole run),
  `toolkit/authsrv/test_clickecho.py` (**MOVECODE-K2, and it is a STRUCTURAL test on
  purpose.** The change lives inside the `0x003E` handler in `handle()`, which needs a
  socket, a key exchange and a live client to reach, so there is no pure function to
  drive the way `_keepalive_ok` and `_position_verdict` can be. What CAN be pinned is
  the shape of the decision, and here the shape IS the claim. **§2 is the load-bearing
  one**: the echo must fall through on `not fresh` and on NOTHING else, because
  `geo-unplaced` and `geo-blocked` are a different defect — FINDINGS §1i.5 splits the
  17 refusals into 13 staleness and 4 geometry — and a flag that quietly answered
  geometry refusals too would be re-running the railing graveyard under a new name.
  Planting the exact regression (dropping `and not fresh`) makes it go red, which was
  verified rather than assumed.
  **§2 CHANGED 2026-08-28 and the change is worth reading, because the check did
  exactly its job and then had to be rewritten.** MOVECODE-R1-B2
  (`--echo-any-refusal`, FINDINGS §1p.10 item 2) widens the gate to
  `bool(CLICK_ECHO) and (ECHO_ANY_REFUSAL or not fresh)` — deliberately crossing the
  scoping the paragraph above defends, on the warrant that retail has no freshness
  precondition at all (§1p.3: 22 of 32 live clicks answered with a report over 1.0 s
  old, 5 with no client position ever reported). The old check pinned the literal
  string `k2_echo = bool(CLICK_ECHO) and not fresh` and went **red the instant the term
  moved**, which is what a source-shape pin is for. It now pins three things instead of
  one spelling: that `not fresh` is still *a term* (so K2 remains runnable as its own
  arm rather than being silently merged into R1-B2), that the only widening term is
  `ECHO_ANY_REFUSAL`, and that `ECHO_ANY_REFUSAL` defaults False — and the original
  scope claim is now **evaluated rather than grepped** (with the flag off, a fresh
  click cannot echo whatever `placed` and the clip said). The match is
  whitespace-normalised because the gate wraps across two lines and the old form would
  have been pinning the indentation. **§1 also gained the CLI guard**: passing
  `--echo-any-refusal` without `--click-echo` must `raise`, because it is one term
  inside `CLICK_ECHO and (...)` and alone it changes nothing — a run launched on it
  would produce a clean capture of the *shipped* policy filed under the new arm's name,
  which is how K1 got reported through two fires. **§3 pins the POINT**, which is what killed
  `--heading-grant` twice over: it must be the click's own `dest`, never
  `state["pos"]`, never clipped. It also counts the `continue`s between the gate and
  the send and requires exactly TWO — the refusal the echo skipped, and the RATE GATE
  the echo passes through **on purpose**, since an echo that bypassed
  `GRANT_SUPPRESS`'s floor would out-run retail's own 0.49 s cadence the way the
  reproduction's 0.13 s did. A third would be a path silently swallowing the echo.
  Writing that check found the second `continue` and turned an assumption into a
  documented design decision. **§5 is the negative control**: with the flag off,
  `bool(False) and X` is False whatever `X` is, so the gate reduces to the shipped
  `if not D1_LEAD:` and the refusal message is untouched — and the echo's own log line
  must read differently, because two decisions printing the same line is how a run gets
  scored as the wrong arm. Floor 19 against a green run of 25, and every section is
  process-free so the floor is the whole run),
  `toolkit/authsrv/test_planerepair.py` (**the plane-lock repair and the
  plane-echo tripwire, MOVECODE §1z-d** — built from r5stuck, the first
  captured client-side movement LOCK: a client that crossed a plane boundary
  carrying its old plane word could not solve a path from the impossible
  plane and so could never walk to ground that would re-plane it, while the
  server accepted 82 byte-identical 0x003D reports over 40.4 s and echoed the
  impossible plane back in 43 grants without one log line naming it. **The
  design under test is the pre-commit review's, not the first draft's**: the
  draft disarmed on every 0x0047 stop-report, and replaying the source
  capture through it refuted its own registered prediction (the measured
  lock INTERLEAVES stops — a victim mashes keys — pushing the first fire
  from 5.1 s to 9.3 s); stops are now ignored and evidence freshness is the
  GAP stream-continuity bound, derived from that capture's own gap structure
  (a 2.47 s intra-episode gap must accumulate, the 10.3 s inter-episode gap
  must re-arm — both are checks here). §1–§3 hold `plane_repair_track` to
  the measured signature and — the part that matters — to every clause that
  must DISARM it, because the failure mode of a repair is firing on a client
  that is fine: the moving no-clipper (r5bridge's shape, re-arms every
  report), the DECODED deck-stroller whose plane the mesh OFFERS (the check
  says out loud that the 9/198 hole — deck coverage our decode LACKS — is
  the opposite case and IS restamped after 5 s frozen; that residual is
  priced in the constants block, not prevented), the ambiguous stack
  (plane_at's None refuses), the off-mesh point, the NaN coordinate (refused
  before `containing()` can raise `int(nan)` out of the recv loop), the
  trust-refused report (which DISARMS rather than skips — the anti-teleport
  inheritance), the pure-turn report (movementType 0, never seen in 7,988
  corpus records, guarded per the cancel arm's own precedent), and the stale
  stream (a report gap over GAP re-arms — one keypress cannot inherit a
  minutes-old streak). §4 pins the wire: numbered fires at most once per
  MIN_INTERVAL, at the client's OWN frozen point (no positional yank),
  labelled PLANE-REPAIR (attribution-by-label is the licence for a third
  0x002C sender), with `plane_repair_due` rows on reason TRANSITION only —
  and that a fire heals `zl_last_grant_plane`, or the SAME packet's
  zero-lead grant would restamp the sync copy with the plane the 0x002C
  just corrected (the review's skeptic finding 1).
  §5 pins the tripwire's one load-bearing property: the emitted values are
  **UNCHANGED** — it observes the impossible echo the stuck session made 43
  times silently, and a mutation here is the exact twice-refused regression
  — plus a control that r5bridge's 9 legitimate deck grants stay silent and
  that the sync model is byte-identical with and without a mesh. §6 pins the
  composition note to appear only beside a second 0x002C policy, and the
  bare call to stay `(None, [])`. §7 is source order on the 0x003D call site
  (its first draft matched the function DEF instead of the call — the
  verify-the-operand trap, kept as a comment) plus an ABSENCE pin on the
  0x0047 arm: the refuted stop-reset reappearing there is the failure it
  guards. §8 proves the r5stuck premise against the REAL map-280 mesh —
  offers exactly [0], resolves 41→0 — runs the verdict against the real
  `PathingMap` unmodified, and closes the review's last gap by driving the
  ambiguous door on REAL stacked geometry (r5bridge's deck point offers
  [0, 37]; a claim of 5 refuses); ledger-skipped, never silent, without the
  archive. Floor 36 against a green run of 41 — exactly the 5-check
  real-mesh section of headroom. ~2 s with the archive),
  `toolkit/authsrv/test_position_trust.py` (the position-trust policy: it may
  refuse a client-reported position, but it may never **latch**. The old
  `_adopt_client_position` refused anything more than `900 u` from
  `state["pos"]` — the value the refusal was preventing from being corrected —
  so once the model was more than 900 u wrong every true report was also more
  than 900 u away: run `20260819T113049` refused **50 reports, 36 of them
  consecutively**, 21% of everything the client said, and only recovered because
  `0x0047` writes without asking and the player happened to stop. Scored over
  the **72** refusals the four harness runs actually printed (7 + 11 + 50 + 4,
  from the servers' own `[map] ignoring a Nu jump` lines and **not** from a
  replay), asking whether the client's next report is reachable from the point
  we refused or the one we preferred at 478 u/s — the game's most generous speed,
  Junundu Tunnel at +66%: **client right 71, guard right 0, undecidable 1.** Two
  numbers this file deliberately does not use: an earlier replay reported 85
  refusals and a largest true-but-refused drift of 18,647 u, and both are
  artifacts — the servers printed 72 and the largest drift in the whole harness
  tree is 4,116 u. A test pinned to 18,647 would have gone red forever against a
  number no server ever produced. **§1 is the invariant that shaped the fix**:
  the budget is `max(900, 580 · dt)`, so it is never *smaller* than the old flat
  radius, asserted over 20 s of silence in 10 ms steps — a tighter design was
  drafted, costed at 8 newly-refused true reports across the corpus (all 8 in
  the one run whose displacements have no established cause) and thrown away.
  §2 is the headline: twelve presentations of the real 2,844 u jump never refuse
  more than `CLIENT_POSITION_REJECT_STREAK` in a row. §3 asserts silence widens
  the budget and that the modal 0.5 s cadence still refuses once, so the guard
  is loosened rather than deleted. §4 asserts position and plane are **one
  fact** — the `0x003D` arm used to write the plane unconditionally 28 lines
  above the position guard, so the server held plane 18 against a point its own
  navmesh puts on plane 0. §5 asserts a refusal does not refresh `pos_seen`,
  without which the budget stops growing exactly when the model is most wrong.
  §6 asserts the telemetry can say `accepted=False` — it was a **literal `True`**
  emitted from the stop arm only, so the flagship capture's JSONL held 5 of 62
  reports and none of the four refusals, our own instrumentation failing the
  "a check that cannot fail is not a check" rule — and that the stop arm now
  *declares* its unconditionality rather than holding it by omission. **§7 locks
  the candidate warp fix**: `--stop-echo` ships OFF, and the echo's destination
  must be the syntax-tree node `reported` — the client's own figure, so the
  message is zero-distance *by construction*. Rewriting it to `state["pos"]` or
  to the click's `dest` would turn a no-op into a real teleport at the player on
  **every stop**, which is precisely the damage the `0x0047` arm's own comment
  records ("teleporting a player nine units is pure damage"); a grep cannot tell
  those apart and the tree can. **§8 locks the direction vector to UNIT LENGTH**,
  and it is a lock on an *inert* bug on purpose. We answered every keyboard
  heading with `list(heading)` -- the client's own `0x003D` vec2, a
  **displacement** of magnitude 765.017..768.000 -- in a field retail fills with
  a unit vector in **3,789 of 3,789** live samples against our **4,704 of 4,760**
  at 765-768, two populations with zero overlap, decoded from the wire bytes on
  both sides. It reached nothing: setter `0x00602660`'s case 1 is a bare dword
  copy and case 4 is `Vec2Negate` into the same tail, so the client stored our
  number **raw** for 82% of sends -- but the only float read of `+0xBC` inside
  `AgAgent` is the lazy angle cache at `0x005FFA1D`, which calls `atan2`
  (`0x005BCA00`, CRT descriptor `\x05atan2`), and atan2 is scale-invariant. The
  section exists because *verbatim-first* is how this repo decides what is true,
  and a wire field disagreeing with retail by 768x is a standing invitation to
  explain some future symptom with the wrong cause. It asserts one send site,
  that the payload's vec2 is the node `unit` and **not** `list(heading)`, the
  zero-length guard (55 of our own sends carried `|v| = 0`, a `ZeroDivisionError`
  in the naive form), and -- against a 2026-08-19 workflow recommendation that
  was **refuted in the same pass** -- that the trailing byte is still `moving`,
  the client's own `movementType`, which retail echoes in 2,215 of 2,254 (98.27%)
  and which is not an angle. Its **control hands the matcher `list(heading)` on
  purpose**, because the rejecting branch is the one that never runs against
  healthy source and so is exactly the branch a typo would silently disable.
  **§9 locks the shape of `--client-endpoint`**, the FIFTH candidate fix, against
  the two defects that made the fourth warp the owner's character. It ships OFF;
  its send must NOT contain `clip_to_walkable` (our navmesh shortens a leg
  wherever it thinks a wall is, and where it disagrees with the client's own
  collision we grant a point short of where the player is really going -- the
  authoritative copy stops early and the gap that becomes the warp opens); and it
  must derive the point from `reported`, not `state["pos"]` (equal on every
  ACCEPTED report, and different in exactly the window a refusal opens, which is
  when our model is least entitled to name a destination). Both matchers run only
  against healthy source, so both are branches a typo would silently disable --
  the control hands them source carrying both old defects and requires them to
  still fire. §10 replays the capture. **§11 locks `--resync`**, the SEVENTH
  candidate and the first one aimed at the copy the player actually sees.
  `GAME_SMSG 0x002C AGENT_UPDATE_POSITION` is the only catalogued primitive
  whose handler reaches BOTH of the client's copies with no gate — read out of
  the pinned pristine 38797 image at `0x005FDA50`: `AgTrack::Clear` first
  (`0x005FDA78`, which zeroes `clientControlled` and so disarms the three-gate
  desync test behind it), then `SetPosition` on the SYNC array
  (`[esi+0xe8]` → `0x005FDAE5`) and on the ASYNC array (`[esi+0x14c]` →
  `0x005FDB49`). **It is also the message an earlier build sent and had removed
  as "the warp the player described"** — because that build sent OUR
  INTEGRATOR'S position, and "five went out and three were arrivals, carrying
  the client 630, 189 and 765 units"; 765 is exactly one heading vector, i.e.
  the integrator had walked a whole leg the client never walked. The entire
  difference between a fix and that regression is which value lands in the
  payload, and `state["pos"]` is nine characters from `state["client_pos"]`, so
  most of the section exists to make that keystroke red: the payload is asserted
  behaviourally against a state where the two DISAGREE, the send site's vec2 is
  asserted as the syntax-tree node `list(payload)`, and `state["client_pos"]` is
  asserted to have **exactly one writer in the file** — the accept path. **§2g (MOVECODE-1z-bg, 2026-09-04): THE SLIVER ORIGIN.** The origin test was exact containment and the client's wedge-tip reports sit ≤ 0.5 u outside our edges (179 zero-leads in 26 runs). A `SliverPM` whose mesh begins at x = 0 pins: a 0.5 u sliver origin gets a real lead walked on the plane clip and stopped at the wall like an inside origin; ROUTER-B3's door stays shut (a ray into the edge returns the START, never the unclipped ray); 1.5 u is still `origin-unwalkable`; two planes with no report word refuse as `origin-ambiguous`; a mesh without `on_mesh`/`plane_near` keeps the exact test; the plane-blind arm never opens the door; the revert arm (`--lead-origin-exact`) reproduces the zero-lead; and the source locks (default ON, the flag bound from argv, the ambiguous word, `plane_near(prefer=the report's plane)`). Floor 110 → 118.

  **That lock went red for real on 2026-09-02, and the fix is worth reading
  before the next one.** ANIMREF-RE §39 (`807ab89`) added a second writer in
  `_press_supersedes`: when a press ends a click leg the server sends a 0x002C
  at the body's modelled position, and that build wrote the model into
  `client_pos` too. The reason was real — `_click_leg_start` falls back to
  `client_pos or pos`, so a report left at the leg's START is what
  `_approach_send`'s snap guard reads, and it would re-pin the body back
  there — but the value is `_click_leg_start`'s own dead-reckoned lerp, i.e.
  the integrator, landing in the field two wire senders read under "NEVER OUR
  OWN POSITION" (`_resync_verdict`) and "the report in hand, and nothing else,
  may be sent" (`_keepalive_ok`). Three things make it a second POLICY rather
  than a split assignment: it stamped `client_pos_at = now`, so a modelled
  value passed the `RESYNC_MAX_REPORT_AGE` freshness gate whose whole job is
  to bound how far the client could have moved since it SPOKE; it fed
  `_click_leg_start`'s own fallback, so the integrator became its own input
  wearing the client's label; and **it wrote position and instant but not
  `client_plane`**, splitting the triple `_take_client_position` writes as one
  fact and leaving the cast-stop reckon — which requires all three and
  type-checks the plane — free to pair a modelled point with a plane measured
  somewhere else. That is the exact split `_take_client_position`'s own
  comment was written to close, re-opened from the other end.

  The fix FORGETS the report instead of overwriting it
  (`_forget_client_position`, popping all three keys): a 0x002C at a modelled
  point means we no longer know what the client would say, so every consumer
  fails closed until it speaks again — `_resync_verdict` "no-client-report",
  `_keepalive_ok` "no-report", the cast-stop reckon "no-report" — while
  `_click_leg_start` drops to `state["pos"]`, which the caller sets to the
  placement one line above, so the snap guard gets §39's answer by the same
  arithmetic. This is `cast_stop_pin`'s pattern, not a new one: that field
  already exists so a pin WE sent out-ranks a report made before it. The
  section now pins the MECHANISM as well as the count — the triple is gone
  after a supersede, the snap guard still reads the re-pinned point (the
  positive control), and `--press-waits-for-leg` forgets nothing (the arm
  that sends no 0x002C must not clear a report nothing contradicted). Each
  was shown red on its own mutation: reverting to §39's write reddens the
  count and the forget, dropping `state["pos"] = model` reddens the snap
  guard, forgetting ahead of the flag guard reddens the control.

  **Closed 2026-09-03, and the closure carried the rule the first fix only
  implied.** `_approach_send`'s own snap re-pin was the other 0x002C at a
  modelled point, and it did not forget: not a `client_pos` writer, so the
  lock could not see it, and both consumers that would be hurt ship OFF —
  but the day either is turned on, the send re-seeds the sync model onto its
  own point (`_note_wire_move`: `sync_from = point`, `sync_to = None`) and
  `_keepalive_ok` then computes `sep = hypot(client_pos − sync)` with
  `client_pos` still at the click leg's START. That separation is the one
  which just fired the re-pin, so it is over `KEEPALIVE_SEPARATION` **by
  construction**, and the grant goes out at the leg start — walking the body
  back down the leg it just walked. `_resync_verdict` has the same shape and
  hard-SETS both copies there instead.

  **The rule is the ASYMMETRY, and it is about the POINT'S SOURCE — not the
  opcode, not the call site.** A 0x002C at a point our model computed
  CONTRADICTS the last report, so forget it; a 0x002C at the report itself
  AGREES with it, so keep it, because dropping it would fail every consumer
  closed over a fact we still hold. All five 0x002C senders sort by that one
  test: `_press_supersedes` and `_approach_send`-on-a-modelled-point forget;
  `_maybe_resync` and `_agtrack_maybe_repin` send `client_pos` verbatim and
  keep. `_approach_send` is the ONLY site that can be either — its point is
  `_click_leg_start`'s, which is the leg lerp when the client has been silent
  and the client's own report otherwise — so the branch condition was split
  out as `_click_leg_source` (returning `"leg"` / `"report"` / `"pos"`) and
  `_click_leg_start` now reads its branch from there. One condition, one
  place: a second copy of it is a second place to disagree, which is the
  defect shape the source lock one field over exists to catch.

  Section 11 gained four checks for it, all fixture-free: the forget; the
  positive control that the re-pin still reaches the follow leg the same call
  arms (the payload is read BEFORE `state["pos"] = model` and the follow's
  start AFTER it, so the check brackets the write the forget depends on); and
  **both** controls the asymmetry needs — a re-pin firing at the client's own
  report forgets nothing, and the `repath=True` arm, which runs no guard at
  all, forgets nothing either. Each went red on its own mutation with clean
  attribution: deleting the forget reddens only the forget (that is the
  pre-fix behaviour), dropping `state["pos"] = model` reddens only the
  positive control, dropping the `src == "leg"` test reddens only the report
  control, and hoisting the forget to the top of the function reddens both
  controls and neither of the first two. Floors 223/231 → 227/235, read off
  real green runs of each configuration.

  **One 0x002C site does not sort cleanly and is recorded rather than
  fixed:** the plane repair sends the report's own POSITION with a CORRECTED
  plane, so the position half agrees with the record and the plane half
  contradicts it. It runs immediately after `_take_client_position` has
  written `client_plane` = the plane being repaired, so the record is left
  naming a plane the client no longer holds — half a fact, the state
  `_forget_client_position` exists to refuse. Forgetting is the wrong answer
  (the position is still good, and the repair's whole point is that it knows
  the right plane) and rewriting `client_plane` would be a second writer of
  the record, which is the other thing refused. Its readers are `--resync`
  and `--cast-stop=pin`, both OFF, so it is latent like the rest. It also
  asserts the flag ships OFF and that with it off a state that *would* fire
  sends nothing **and records nothing**; that the three constants carry
  derivations rather than choices (the trigger is the client's own 100.0 u
  match radius at `0x00946560`, three times under gate 1's real 299.332591 u
  cut; the rate limit sits under its derived ceiling of `299.332591 / (2·288)` =
  0.5197 s, the shortest time in which two copies moving directly apart can
  accrue a full gate's separation; and `RESYNC_MAX_REPORT_AGE · 288 = 100.0 u`
  exactly, so **the staleness bound IS the harm bound**); that a payload with no
  accepted client report behind it is refused with 5,000 u of our own drift on
  the table; that the age bound is inclusive at the bound, refuses one
  microsecond past it, and refuses a **negative** age too (clock skew sails
  through an upper-bound-only test); that twenty fireable reports over 1.9 s
  produce 4 sends and not 20, **and not 0**; that 50 u apart sends nothing; that
  the SYNC model fails closed when unseeded, walks a granted leg at 288 u/s
  rather than teleporting to its end (a model that parked instantly would read
  every legitimate click-walk as a 2,880 u desync), parks on the point, and
  follows a `0x002C` we send; and that the encoded bytes are the schema's —
  `msg_header / dword / vec2 / word`, 16 B declared and 16 B produced, compared
  **byte for byte** against a hand-packed struct because field order is the one
  thing this project has already got wrong on a movement message. Two controls:
  one asserts the function under the matcher really does mention `state["pos"]`
  (it logs it beside every verdict) so the matcher is not judging an empty
  set, and one hands the matcher `list(state['pos'])` on purpose and requires it
  to still reject. It also asserts the flag's own startup banner is printable —
  a `U+26A0` in it raised `UnicodeEncodeError` on a default Windows console
  while this was being written, so the flag would have killed the very run it
  exists to enable before a packet went out; the scan is against **cp1252**
  rather than ASCII, because the em dashes elsewhere in `authsrv.py` are fine
  and a blanket rule would be wrong, and its control plants a `U+26A0` and
  requires the scan to still see it. **§12 locks `--grant-suppress`**, the
  EIGHTH candidate and the first that acts by sending **less** rather than by
  sending something better. Three captures of 2026-08-20 earned it: keyboard
  only (`182554`) is 283-287 u/s every interval with zero clicks, zero grants
  and **0.00 hard jumps/min**; five clicks the server *refused* (`182934`) is
  zero grants and zero warps; and the reproduction (`183311`) is the owner
  holding S while spam-clicking forward — **196 clicks → 140 grants in 44 s**,
  one every 0.13 s, **five hard jumps** (p50 1,372 u, max 3,010 u, 6.82/min)
  with four of the five landing 0.10-0.23 s after a grant. `0x0029` is
  SYNC-ONLY, so a grant sent mid-keyboard drives the authoritative copy away
  from the rendered one *and* re-runs the desync test that snaps them together
  past 299.332591 u. The section asserts the flag ships OFF and that with it off
  a state that would be refused twice over grants anyway, records nothing, and
  does not even clear a pending it finds; that both constants carry
  derivations — the 3.0 s locally-driving window is sized off **n = 3,420** gaps
  between consecutive `0x003D`-moving reports with no `0x0047` between them
  across **987 `ours` captures** (p50 0.500, p90 1.801, p99 2.737, with a real
  mode at 2.74-2.79 s: 144 exceed 2.00 s and only **9 exceed 3.00 s**, so 3.0
  covers 99.74% while 2.0 would open a hole in 4.2%), and the 0.5 s grant floor
  is fixed by **two independent derivations landing on the same number** —
  retail's own median player inter-grant gap of 0.492 s over 2,855
  player-directed `0x0029`, and the same `299.332591 / (2·288)` = 0.5197 s
  separation ceiling `--resync` uses. Rule 1 is asserted at **both edges**,
  inclusive at the window, lapsed one microsecond past it, and **armed on a
  negative age** because clock skew sails through an upper-bound-only test; its
  control is the cleared latch granting the very same click, without which
  "refuse everything" passes. Rule 2 is bounded **above and below** (twenty
  clicks over 1.9 s produce 4 grants, not 20 **and not 0**), driven through the
  real `_note_wire_move` hook so the clock under test is the server's own — the
  click arm, the heading arm, the endpoint arm, the stop echo and the click
  sweep all grant through it, and a limit fed from the click arm alone would be
  blind to four senders. The deferred half is asserted to send once, be
  consumed, carry its two plane words in the click arm's order, be **dropped**
  rather than delayed once the player keyboards again, and expire inclusively at
  `2 · GRANT_MIN_INTERVAL`. Structurally: `state["kbd_moving_at"]` has **exactly
  two writers**, one conditional on the client's own `moving` and one flat
  `None` — deliberately *not* `state["walking"]`, which the click arm itself
  clears, so keying rule 1 on it would have let the first click of the
  reproduction disarm the latch and the other 195 straight through; the three
  geometry reasons survive verbatim and their refusal is strictly **before** the
  new gate, since those lines say something about the map and are what the owner
  reads live; the arm has one grant send and it sits after the gate; and
  `state["grant_pending"]` is a single assigned slot with **zero appends**,
  which is the whole difference between rate-limiting and deferring the storm by
  one interval. Its controls are handed the defects on purpose — a latch keyed
  off `state["walking"]`, and an `elif` chain where body-scoped matching sees 1
  send while `ast.walk` sees 2 (the real bug this check caught while being
  written). **§13 is the replay, and it is the treatment and its control from
  the wire rather than from a fixture we wrote**: `196/196` of the
  reproduction's clicks refused as locally-moving with **zero** grants
  surviving, `5/5` of the ordinary capture's clicks **permitted**, and the
  keyboard-only run carrying no clicks to decide at all. Either half alone
  proves nothing — a policy that refuses everything passes the first and today's
  code passes the second — and the section says out loud that it replays rules 1
  and 2 only, the two geometry refusals running upstream of them and not being
  modelled.
  **RULE 1 GAINED AN OPT-OUT 2026-08-28 and it is checked in the same block that
  pins rule 1 itself.** MOVECODE-R1-B1 (`--answer-kbd-click`, FINDINGS §1p.10
  item 1): rule 1's refusal is OURS and not ArenaNet's — over the live corpus
  **7 of 32 clicks arrived with this latch armed and retail answered every one
  within one RTT**, 635–2,445 u from any D1 lead prediction, so they are click
  answers rather than lead refreshes. The flag lets the click fall through, and
  the four checks are built so that a flag deleting *too much* cannot pass: the
  default is asserted False; the identical state that returns `locally-moving`
  with the flag off returns `grant` with it on (each is the other's control);
  the `keyboard_age` is asserted still present on the verdict, because
  **GRANTED-with-a-non-null-age-inside-the-window is unreachable with the flag
  off** and that pair is therefore an exact offline signature *and* the
  registered exposure floor; and — the load-bearing one — a click inside
  `GRANT_MIN_INTERVAL` must still come back `rate-limited`, because rule 2's
  hold-and-coalesce IS the pair contract REALFIX §0.15 actually states, and a
  flag that removed both rules would pass every other check in the block. A
  final check restores the global and re-asserts the refusal, since a module
  global left set by one section leaks into every section below it. **The reason
  string stays `grant` on purpose**: `grantsim.py:2000` filters `w[2] ==
  "grant"` and `policyreplay.py:267` switches on `locally-moving`, so a new enum
  value would have silently shrunk two scorers rather than erroring — the
  greppability was traded for that, and `keyboard_age` carries the information
  instead. **§14 IS `--zero-lead` (REALFIX-P2), AND IT IS THE FIRST SECTION
  HERE THAT EXECUTES A RECEIVE ARM** rather than only matching its syntax tree.
  Two of that flag's claims are behavioural and no AST matcher can reach them --
  a moving report the shipped `turned or not walking` gate would SKIP is still
  granted under the flag, and the very same report sends **nothing** with the
  flag off -- so `receive_arm()` lifts the arm's own statements out of the
  receive loop, wraps them in a function of the four free names they need and
  compiles them against `authsrv.__dict__`. It runs the file's bytes,
  re-extracted every run, and it raises rather than handing back an empty body
  if the arm is ever renamed. The section pins the **payload** (the granted
  point is the client's reported position VERBATIM -- not `state["pos"]`, not
  the clipped `model_dest` -- with both plane words the reported plane and the
  `0x0029` LAST in the burst), **exactly one `0x0025` per burst** whichever path
  asked for it, the **model/wire split** (`state["dest"]` still holds the
  clipped 766 u leg while the wire carries the report), and that a rate-refused
  heading grant is **DROPPED, not held** -- no `grant_pending` key appears.
  `_heading_grant_ok` is checked for PURITY (five calls, one answer, state
  byte-identical after) because `grantsim.py` imports and runs it, for its floor
  at both edges of `GRANT_MIN_INTERVAL`, for refusing a grant stamped in the
  FUTURE, and for **carrying rule 2 ONLY**: the very state the click arm refuses
  as `locally-moving` still grants here, which is the check that stops the arm
  being "simplified" onto `_grant_verdict` -- that predicate's rule 1 would emit
  **zero** grants, because the heading arm arms the latch ten lines before it
  would ask. The two arms' reason vocabularies are asserted DISJOINT
  (`zero-lead`/`heading-rate` against `off`/`locally-moving`/`rate-limited`/
  `grant`) -- **and both halves of that comparison are now READ BACK OUT OF THE
  SHIPPED PREDICATES by driving them**, because the version that compared two
  literal sets could not fail: a mutation that made `_heading_grant_ok` return
  exactly `rate-limited` and `grant`, the vocabularies overlapping completely,
  still printed PASS. A third read cross-checks those two words against
  `grantsim.HEADING_REASONS`, parsed out of that file's syntax tree rather than
  imported, since that frozenset is what the replay filter keys on. The stop
  arm is EXECUTED too and must grant nothing -- a stop-arm `0x0029` **is**
  `--stop-echo` and is refuted -- and the AST half asserts `ZERO_LEAD` is named
  in the heading arm and in **neither** the stop nor the click arm, with the
  heading count as its own positive control. **THE TRUST GUARD IS ADVISORY ON
  THE GRANT PATH, and §14 drives that both ways** rather than leaving it to be
  found in a live run: a report claiming a 40,000 u jump is REFUSED by the
  policy this whole file is about -- `state["pos"]` holds -- and the arm grants
  the rejected point VERBATIM anyway while `_note_wire_move` drags `sync_to` to
  it, which is the exact operand REALFIX-L1's movetap separation metric reads.
  Its control is the same report with a stale `pos_seen`, ACCEPTED, where the
  wire is identical and the model moves too, so what the pair differs in is the
  refusal and not the report. That pair also pins the precise statement of the
  model/wire split: `state["dest"]` is `clip(state["pos"] + vec2)`, equal to
  `reported + vec2` only on an accepted report, and the grant is **not**
  wire-only -- it moves `sync_from`/`sync_to`/`sync_at` and stamps the shared
  `grant_at`. Finally the **composition matrix** is driven cell by cell through
  the pure `zero_lead_composition()`, with its cases taken from the shipped
  `ZERO_LEAD_REFUSED_ARMS` table rather than restated: refusing `--heading-grant`,
  `--client-endpoint` **and `--stop-echo`**, each citing its OWN refutation line
  and naming no other flag, named in the plural with both lines when two are
  passed; allowing `--grant-suppress`, `--resync` and `--click-sweep` each with
  a printed note; and a control that with the flag OFF nothing is refused at
  all. **`--stop-echo` was missing from that list until an adversarial pass
  found `--zero-lead --stop-echo` accepted silently** -- the refusal was keyed
  on "answers the same `0x003D`" and the stop arm answers `0x0047` -- which is
  why the loop now reads the table instead of enumerating cases a test author
  can forget the same way. **AND THE MATRIX'S ANSWER IS ENFORCED AT ITS CALL
  SITE**: an AST read of `main()` requires the refusal to be `raise`d as a
  `SystemExit` and requires every flag the function can decide about to actually
  be passed to it, with a hand-built bad `main()` as the control. Replacing that
  `raise` with a print left all 147 checks green while the server would have run
  the refused combination, and a parameter the call site never fills can never
  fire from a real command line -- which is precisely how `--stop-echo` went
  unrefused. The **startup banner is pinned** for the same reason: `REALFIX.md`
  §4 rests on "the prediction is printed verbatim at startup so it cannot be
  rationalised afterwards", and deleting the retraction and all three numeric
  bounds changed no test, so §14 now requires the retraction, both units of the
  frequency/displacement bounds, the separation bound, the failure signature and
  the invariant-refuting condition to be present in the block's own string
  constants, with a stripped block as the control. **§15 IS `--plane-carry`
  (REALFIX-F1), AND IT IS A MODIFIER ON §14's FLAG RATHER THAN A TENTH
  CANDIDATE POLICY.** It changes ONE wire field: field 4 of the zero-lead
  `0x0029`, which is what the client writes to `agent+0x80` on the **SYNC**
  copy -- a copy one report-chord (~515 u, REALFIX-W2) behind the client, so on
  a plane boundary the shipped payload stamps the *client's* plane onto a copy
  standing somewhere else. **REALFIX-L3 measured that as the trigger for all
  three of its warps**: 8 plane-rewriting above-cut grants produced 3 events
  (476.8, 465.9, 242.8 u, each 0.05-0.11 s after its grant), 28 above-cut grants
  with the plane word *unchanged* produced 0, Fisher exact **p = 0.0078** -- and
  the P0 control carried **7x** the plane-mismatch samples and 97% of its run
  above the gate-1 cut while never moving its rendered copy more than **43 u**,
  so separation and plane disagreement are not sufficient and what P0 lacks is
  the grant. F1 sends instead the plane that arrived **with** the point the copy
  is standing on, which under zero lead is the previous grant's *by
  construction* -- not from the navmesh, because the rejected variant computes
  it as `plane_at(copy_estimate)` and `plane_at`'s 9 failures out of 198 are
  **exactly bridge-over-ground**, which is this map's site. The section reuses
  §14's lifted receive arm with a second module flag set and a per-report grant
  clock, so a rate refusal can sit *between* two grants. It pins the three
  payload cases the spec names -- first grant with no previous (field 4 falls
  back to the current plane, and **not** to 0, which would write a wrong map
  index into `agent+0x80`), a plane change (field 3 = the new plane, field 4 =
  the previous grant's), and no change (both equal, so F1 is **inert off a
  boundary**; without that case a flag rewriting field 4 on *every* grant would
  pass "the payload changed" and be a different policy). **F1 OFF is asserted
  against a hand-written literal** -- opcode, payload and console label for the
  same plane-crossing pair -- rather than against a second run of the same code,
  because code compared with itself agrees by construction. Most of the rest
  exists to prove the delta is exactly one field: carry-ON and carry-OFF runs
  must agree on every destination, on the `0x0025`, on `state["dest"]` and on
  `sync_to`, and differ in field 4 alone, which is the mechanism behind the
  pre-registered "separation p50/p90 unchanged within 5%" -- movetap measures
  separation against `sync_to`, so a run where it moved would mean F1 had
  reached a position. The **named limit** is driven rather than asserted: the
  slot tracks *sends*, not evaluations, so a rate-refused report does not
  advance it (no grant went out, so the copy is still bound for the point the
  last one named) -- and that is also where F1 under-corrects, because the copy
  may be in transit between the grant before last and the last one. Telemetry
  carries `plane_dest` / `plane_cur` / `plane_differs` / `plane_carry` on the
  same `grant_verdict` channel with the reason vocabulary **unchanged**, since
  `plane_differs` *is* the pre-registered mismatch count and `grantsim`'s
  `HEADING_REASONS` keys its replay filter on those two words; a refused
  evaluation records `None` rather than the field 4 it would have sent, because
  writing the counterfactual would put rows in the census that is the falsifier.
  **The composition decision is REFUSE, not document-as-inert**, and both
  directions are driven: `--plane-carry` alone raises at startup because F1 has
  no send site of its own (checked, not argued -- a carry-ON run with
  `--zero-lead` off produces byte-identical wire and no verdict row), so an
  inert flag would run a server identical to the shipped default while the
  operator's log said "F1 arm" and the fix would be credited with a null it
  never earned; `--zero-lead` alone still runs, deliberately, because it is the
  arm F1 is measured *against* and a symmetric refusal would delete the control.
  Its banner is pinned the same way §14's is, on the prediction, all three
  FAILS-IF bounds, the named limit and **the NPC-grounding caveat** -- retail's
  field 3 leads field 4 in 75.4% of 1,245 differing rows, but that population is
  overwhelmingly NPCs and the player-identified version is UNVERIFIED at 87% vs
  39% -- with a stripped block and a present-but-never-printed block as its two
  controls, plus the cp1252 scan — **including the baseline counts, which were
  the one evidential string in that banner nobody pinned**: it read "REALFIX-L3
  observed 11 in X3, 3 in X1, 6 in X5" and those are REALFIX.md §4.1's
  *simulated* `instants planned`, never observed, standing where the primary
  falsifier's baseline goes; L3 produced **8** plane-rewriting grants above the
  cut and 2 below, and the banner now says so and is pinned on it. Floors
  **175** bare and **183** with every capture present, **one per
  configuration** -- a single bare floor protected none of the 8 checks only a
  vaulted machine runs, proved by unhooking one §14
  check: vaulted printed ALL CHECKS PASSED at 146 against a floor of 139 while
  the bare run went red at 138. §10 and §13 are the two fixture-bearing sections
  (4 checks each), each declaring `LEDGER.skip` without its files, and the probe
  that raises the floor reads the same capture names those sections use. §14 and
  §15 are entirely fixture-free, so all 47 and all 23 of their checks land in
  both totals. **Every §15 check was proven able to go red**: 15 mutations
  planted one at a time in `authsrv.py` -- field 4 never carrying, field 3
  following it into the past, the slot advancing on a refusal, the default
  becoming 0, the composition refusal deleted, the refusal telemetry recording
  the counterfactual, `plane_differs` hard-coded, two banner lines removed or
  turned into assignments, a `U+26A0` planted, the call site dropping the
  kwarg, the flag shipping ON, the label drifting on the OFF path, a second
  sending `if PLANE_CARRY:` block, and the zero-lead send made to require the
  modifier -- **15 red, tree restored byte-identical after each**. **A second
  adversarial pass then planted 23 (those 15 plus 13 more) and found ONE
  survivor**: the slot write hoisted from after the `send()` to before it,
  inside the same `if zero_ok:`. It is a no-op only for a send that RETURNS --
  `send()` ends in `sock.sendall`, which raises, and the shipped `send()` says
  so where it explains its own seq gaps -- so §15 now drives a `0x0029` through
  a send that dies (`PcDeadWire`, faithful to the shipped order: the wire-move
  hook before the bytes, the `sent` row after) and requires the slot to name the
  last plane that reached the WIRE. That is the 23rd check. The same pass found
  that dropping the `plane_differs` kwarg reddened by an uncaught `KeyError`
  raised inside the check's own arguments, which aborts before
  `LEDGER.verdict()` and leaves the floor unevaluated -- so the telemetry checks
  read those four fields with `.get` and FAIL BY NAME, except the refused row,
  where `None` is the answer and presence is asserted with `in`.
  **§16 IS `--arrival-carry` (REALFIX-F1b), AND IT EXISTS BECAUSE §15's FLAG
  FAILED ITS OWN PRIMARY FALSIFIER.** F1's pre-registration — pinned by §15 —
  was "grants whose field 4 differs from the SYNC copy's `agent+0x80` go to 0";
  its run (`20260821T143411`) came in at **5 of 93** against the P2 control's 8
  of 88, every one above the gate-1 cut and every one F1's own **named limit**:
  a *two*-interval lag, where the client had been on plane 18 for two grants
  while the copy was still on 0, so "the previous grant" was already 18. F1b
  changes the operand rather than the field: field 4 becomes the plane of the
  grant the copy has **ARRIVED** at, computed with the client's own destination
  bake (`arrival = send time + |dest − copy| / 288 u/s`, truncated to whole ms,
  with the `|d|² ≤ 1.0` short-circuit arriving at once) over the SYNC model the
  server already keeps — **no navmesh and no new constant**. The section drives
  the three pure functions directly and through the lifted receive arm, and its
  centre is the **in-flight supersede**, which is the whole difference from F1:
  a grant landing while a leg is still in flight re-aims the copy mid-leg, so
  that leg's plane must never become "the plane the copy arrived at" *and* the
  new leg is measured from the **dead-reckoned point**, not from the abandoned
  destination. Both halves are measured rather than asserted — the discarded
  case's leg comes out 288.000 u from the dead-reckon against the 407.294 u it
  would read from the abandoned destination, so "which point did it start from"
  is answered by a number, with the same pair one second later as the control
  (A really has arrived, 21 *is* carried, the leg reads 407.294). The other
  cases: the **first grant** defaults to the current plane (not 0, which would
  write a wrong map index); an **unseeded** SYNC model answers `(None, None)`
  rather than inventing a start point; a **rate-limit refusal** mutates nothing,
  driven at four instants including two past the arrival, and pinned from the
  syntax too — both *read* functions are asserted to contain no `state[...]`
  assignment, because they run on every evaluation; a **stop** leaves the queue
  alone (the copy chases *our* point, not the player's keys); and a **`0x002C`
  hard set** drops the in-flight leg and takes its own plane, because
  `0x006020B0` clears the arrival tick at `0x006021E6` and an entry left behind
  would come due on a leg the client had abandoned. §16 needs a **fake clock**
  where §15 did not, and that is itself the finding: F1's carry is a pure lookup
  with no clock in it while F1b's turns on `arrival <= now`, so a test racing
  the real clock would flip its expected payload on a fast machine. The
  millisecond clamp is checked as **unreachable** rather than exercised — every
  leg in (1.000, 3.000] u ticks ≥ 3 ms, because anything shorter takes the
  short-circuit — which is the honest assertion about defensive code. Payload
  exactness and the flag-OFF **byte identity** are asserted as in §15, and the
  supersede is driven a second time through the real send path at a cadence
  where no leg lands: F1b holds the plane the copy reached (`[7, 7, 7]`) while
  **F1 on the identical three reports sends an 18 the copy is still 0.4 s short
  of**, which reproduces the two-interval lag from the shipped arm. Composition
  is a **three-way** matrix: `--arrival-carry` alone is refused like
  `--plane-carry`; `--plane-carry` *with* `--arrival-carry` is refused as **two
  policies for one wire field** (whichever the send site read, the other would
  be inert, and both print their own pre-registered banner, so a server carrying
  both announces two predictions and can satisfy neither); that refusal is
  ordered *before* the needs-`--zero-lead` one, checked; and `--resync` beside
  it prints the queue-invalidation note. **The banner pins a CHANGED
  prediction, and that is the point of the whole build.** F1b was drafted
  predicting the mismatch count reaches 0 — the falsifier F1 failed — and the
  offline pre-screen (`grantsim --planecarry`, §10 there) says it would reach
  **3**, so the banner pre-registers ~3, names the sub-frame race, prints the
  **corrected baselines** (10 and 6, not the published 8 and 5) and prints that
  F1's own event reduction was **not significant** (Fisher p = 0.196) so nobody
  reads an F1b null as proof either. §14's argv-completeness check was rewritten
  in the same commit to read `zero_lead_composition`'s **own signature** instead
  of a literal list of eight names: adding a ninth turned it red, which is the
  check working, but the only maintenance a literal can prompt is "paste the new
  name in". **AND THE TABLE UNDER THAT PROSE IS PINNED TOO, which it was not
  until a mutation lane deleted it and stayed green.** §16 pinned seventeen
  banner *substrings* and left the three-row counterfactual table they summarise
  free: deleting the rows left 215/215, and rewriting the F1b row to the drafted
  **"0 of 69"** the offline screen had already refuted — beside prose still
  reading "F1b DOES NOT REACH ZERO" and "come in at ~3" — left 215/215 as well.
  The rows are now rebuilt from `grantsim.FIELD4_SCREEN`, cell by cell,
  numerator and denominator, so the banner cannot drift from the scorer; this
  file imports `grantsim` for that constant and `authsrv` never may (grantsim
  imports authsrv, and the server path stays dependency-clean), which is why the
  tie is made on the test side and why §10 there pins the constant itself
  against the live computation. §16's composition refusals also stopped
  **crashing** instead of failing: `ac_alone[:60]` was sliced inside an evidence
  f-string that Python builds *before* `check()` runs, so deleting either
  refusal raised `TypeError` on `None`, killed the section mid-run and left nine
  checks and the ledger's floor unevaluated — caught by exit code, naming
  nothing. Floors **211** bare and **219** vaulted, both re-measured
  (**Extended 2026-08-25 for the --resync staging review**: §11 gains three
  fixture-free checks driving HOLE D's `SYNC MODEL NOT SEEDED` guard — the
  print fires exactly ONCE on an unseeded state across repeated verdicts,
  its refusals still land in the telemetry, and a seeded state never prints
  it — because the review's mutation pass showed the guard had zero
  coverage: condition inverted, every suite green); §16 is
  fixture-free like §14 and §15, so all 33 of its checks land in both. No
  client. ~2 s),
  `toolkit/clientscan/test_movesync.py` (SEPARATION -- the quantity that
  actually predicts a warp, and the guard on the two instruments that reported
  the wrong one. `warpscan.py` scored a big client step against the points we
  had GRANTED and answered "NOT near any grant" for **10 of its 12** detections;
  that line was the finding, not a puzzle -- the landing point sits on the
  server-authoritative agent's glide path, because `movetap` reads the SYNC
  array while the client reports from the copy it predicts and renders. And
  `movetap` scored itself against `seconds * hz * 0.5`, half the REQUESTED rate,
  while the reader sustains ~13 Hz against a default request of 50, so it
  printed FAIL over the very run that overturned this arc's mechanism. §1 pins
  the clock estimator: the capture stamps WHOLE SECONDS, so every sample reads
  `floor(unix) - t`, the mean is biased low by half a second, and half a second
  at 288 u/s is **144 units** -- the same size as the separation being measured,
  which is why the max is taken and why the estimate must never exceed the
  truth. §2 asserts a pair beyond `MAX_PAIR_GAP` is DROPPED rather than
  stretched, `vaultpath.require_dir()`'s rule applied to time. §3 is the scorer
  against a synthetic resync **and** against a control where both copies leap
  together, so a large step exists and the separation across it does not move --
  **that control was written VACUOUS**, its synthetic steps sitting below the
  300 u threshold so `jumps` came back empty and `all([])` passed it having
  judged nothing; the row count is asserted first now. **§4-§8 guard the four
  defects the 2026-08-19 corpus pass found in `movesync.py` itself**, each of
  which had already put a wrong number into a document, and each guard is
  mutation-proven to go red when its fix is reverted. §4 PINS the bars as
  constants: legacy 300 u, run speed 288 u/s, the hard bar's SPEED arm at
  **400 u/s** (retail's own client intervals top out at 388.80, just over the
  383.04 boost base its wire declares, so a lower bar would start counting
  boosted walking), the 0.05 s dt floor, its DISTANCE arm at **520 u**, and
  `FREE_SILENCE = 300/288 = 1.042 s` as a DERIVED number rather than a chosen
  one. 520 is BRACKETED ON BOTH SIDES by measured data and the test says so: it
  sits above retail's largest step inside 2.0 s (**517.87 u / 1.352 s**) and
  below the smallest of the four ordinary WALKING rows the wide
  `dist>=520 & dt<=2.0s` form would have swept in (**525.3 u at 285.5 u/s**,
  `20260814T090541`). **Both of those are the DECISION RECORD of 2026-08-19 and
  are frozen deliberately** — the live corpus's own extremum has since moved to
  **518.25 u** on seven new stamps, and §16 is what measures it against the
  constant. That 7.4 u gap is why the wide form was REJECTED; it was never
  headroom for the narrow one, which fires below the dt floor where walking
  cannot reach. §5 is a client walking at 288 u/s with a report every
  2 s: **the legacy bar flags 11 of 11 steps and the hard bar flags none**, which
  is how retail scored 6.4/min on the legacy bar with zero intervals above
  400 u/s -- the row count is asserted first. §6 plants a **900 u / 0.13 s** step
  and requires exactly one detection on the SPEED arm, then a **700 u / 0.03 s**
  step and requires one on the DISTANCE arm -- and it no longer carries the dt
  control it used to, because **the distance arm INVALIDATED that control**: it
  planted 900 u over 0.01 s and demanded a REFUSAL, which under the repaired bar
  is a test that the fix does not work. What the dt floor is actually for is a
  SMALL displacement over a near-zero interval, so the control is now **25 u over
  0.01 s** (an implied 2,500 u/s, and still not evidence) with the SAME 0.01 s
  carrying 900 u required to be CAUGHT beside it -- the arm is a distance test,
  not a dt test. Every fixture's row count is asserted before its verdict. The
  bar is spelled TWICE and §6 exercises both: `hard_steps` for the wire-only path
  and `score(min_speed=...)` for the paired one, which carried the identical
  blindness and which no vault replay would have caught (§11's movetap window
  happens to exclude the only corpus row that would have shown it).
  §7 builds a LEGACY-SHAPED capture -- `position_report` rows at the stops only,
  a full `0x003D` stream between them -- and requires `--wire-only` to read the
  SPLICED stream `warpscan.load` has read all along: the same walk reads **0
  jumps spliced and 2 stop-arm-only**, i.e. the source alone decides whether the
  client "jumped". §8 is the refusal semantics, and its fixture is
  `20260811T173940` in miniature: dense 0.25 s blocks separated by 5 s silences,
  so the **MEDIAN gap passes the old 0.5 s cadence gate** while the client walks
  1,440 u inside each silence. It asserts the coverage refusal fires, that a
  dense capture does NOT trip it (a gate that always fires is a constant), and --
  reading the tool's real stdout -- that **every legacy count line sits BELOW its
  refusal and is marked `refused`**, because the "5 unexplained jumps" hole was
  minted by quoting a number printed above a REFUSING line. §8 also pins the
  other half of that rule, which the first pass got backwards: **a refusal must
  not suppress a COUNT.** The `MIN_INTERVALS` floor used to `return` before the
  hard section, so a nine-interval capture carrying a 3,000 u impossible step
  printed a bare tally; only a per-minute number needs intervals, and a count and
  a magnitude need no denominator at all. The fixture is exactly that capture --
  **9 intervals, one 3,000 u step** -- and it requires the count, the magnitude
  and the excess to print while **no `/min` appears anywhere in that output**.
  (Measured impact today is nil: 10 vault captures sit under the floor and not
  one carries a hard or a >=300 u step, which is what makes it cheap now and
  expensive to discover later.) §9 asserts `movetap`
  now calibrates its floor against measured capability and survives Ctrl+C with a
  verdict. §10 is the wire-only geometry, which asks the same question of a
  capture with NO movetap and still refuses to reconstruct anything: a resync
  landing point is a *reading* of the authoritative agent (measured at 1.0-59.5 u
  from movetap's, n=13), so the test is three measured positions and a geometry
  question -- does the landing lie on the segment from where the client said it
  was when we granted, to the point we granted? §11 replays the pair that
  established the mechanism (`movetap-20260819T171436` + `authsrv-20260819T171153-c1`):
  183 pairs, 13 resync jumps, separation **587 u -> 22 u, a 96% collapse**, with
  THREE things that could refute it -- pairing 7 s out of true reproduces only
  34%, the alignment sweep must PEAK at the offset the 8,573 timestamps gave
  (never fitted to maximise the headline), and **all 13 must survive the new hard
  bar**, or the collapse would be a claim about a different population than the
  one the mechanism was established on. **That last equality survives the
  distance arm by LUCK, and §11 now pins the luck rather than resting on it**:
  the whole capture gains a row under the repaired bar (19 -> 20, the
  617.0 u / 0.0324 s step at t=138.687), and it disturbs nothing here only
  because the movetap window is **[163.361, 220.619]** and 138.687 falls OUTSIDE
  it -- which is where the operator happened to start the reader, not soundness.
  §12 replays the **DEFAULT-build** capture
  `authsrv-20260819T145717-c1.jsonl`, the one carrying the corpus's biggest
  warps, on the verdict-bearing population: **7 hard jumps, 1.31/min of span and
  5.66/min of actively-reported time** (both denominators, because 77% of that
  span carries no reports), magnitude p50 1,969 u and max 3,405 u, EXCESS OVER
  BUDGET p50 1,208 u and max 3,165 u, 4 of 7 landings on-path against 0 of 7 for
  an unrelated grant at perp **78.3 u against 1,582.2 u** -- **of which 5 of the
  7 are DEGENERATE** (the grant-time report IS the pre-jump record, so the
  landing sits on its own segment by construction), leaving a non-degenerate
  **n of 2, on-path 2/2**, which is the whole of the non-tautological evidence on
  this capture. The tool prints that qualifier and the test used to assert
  nothing about it, so the contaminated 4/7 travelled alone; `hard_degenerate`
  and the clean subset are both pinned now, and the `cperp_p50 > 5*perp_p50`
  ratio has a FLOOR on its denominator (`perp_p50 > 1 u`, plus an absolute
  `cperp_p50 > 500 u`) because on a fully degenerate capture that perp is 0.0 and
  the ratio would certify the tautology. §12 also pins the three things the
  adversarial pass found unstated. **The rate's denominator is borrowed**:
  "actively reported" is the sum of gaps `<= FREE_SILENCE`, the 300/288 constant
  this file calls never-a-verdict, and the SAME 7 jumps read **14.21/min at a
  0.30 s threshold, 5.66 at 1.042 s and 3.40 at 5.00 s** -- a 4.2x spread with
  the numerator untouched, so the threshold and that sweep are asserted present
  in the real stdout. **2 of those 7 hard intervals are THEMSELVES longer than
  the threshold** (3.237 s and 1.485 s), i.e. they happened in time the
  denominator excludes, and the output must RECONCILE it rather than let the rate
  imply otherwise. And the legacy "of which N are walking" line is now EXHAUSTIVE
  in the printed text as well as the dict -- **31 = 23 walking + 7 hard + 1 at
  360.3 u/s that is neither** -- because a partition that does not add up invites
  the reader to complete it with the other category. `values[2]` (plane) is
  carried through `load_wire_reports` and flagged: **1 of these 7 straddles a
  flip**, 6 of the corpus's 64 hard rows do, and it is ANNOTATION not exclusion
  since planes 0/18/19 share the x/y frame here. The legacy bar is REFUSED on
  this capture, a refusal the old median gate missed on a p50 of 0.254 s.
  §13 replays `authsrv-20260811T173940-c1.jsonl`, the capture that
  minted the hole: 158 spliced positions against **28** `position_report` rows,
  **5 legacy jumps from the wrong source and 2 from the right one**, and ZERO
  clearing the hard bar -- the client walked the whole way. **§14-§16 are the
  distance arm's own replays.** §14 pins the two counts that MOVED, because a
  guard that only asserts the new bar equals the new bar cannot go red when the
  arm is reverted: `20260819T182652` reads **13 hard rows where the speed-only
  bar read 11**, and `20260819T171153` reads **20 where it read 19**. The three
  restored rows are 740.7 u / 0.0318 s, 617.0 u / 0.0324 s and 582.1 u /
  0.0331 s -- all ~32 ms, because a resync emits a report either side of the
  snap, so the old dt refusal was ANTI-correlated with the mechanism it was built
  to find. Each pair arrives in SEPARATE TCP frames (c2s seq 465->466, 50->51,
  190->191, each a distinct 26-byte read), so 32 ms is a real client cadence and
  not decode-loop coalescing. §14 quotes MAGNITUDE and EXCESS OVER BUDGET
  (740.7 u, excess 731.6 u = 2.57 s of walking at 288 u/s) and NEVER the implied
  velocity as a headline -- for a discontinuity that 23,279 u/s is a denominator
  artifact the event itself created, so it is printed labelled as the gate's own
  input. Its control is the WIDE form: corpus-wide `dist>=520 & dt<=2.0s` adds
  four ordinary walking rows at 284-286 u/s across ~1.85 s gaps
  (`20260818T103840` 538.6 u, `20260819T150522` 533.6 u, `20260816T131839`
  528.5 u, `20260814T090541` 525.3 u) while the narrow form adds exactly the
  three genuine ones -- **61 -> 64 hard rows over 961 vault captures, 4,582
  intervals**. §15 pins the count that must NOT move: `20260811T173940` still
  reads **0 hard of 157**, and its 14 sub-0.05 s intervals top out at 14.1 u.
  §16 RE-MEASURES THE CALIBRATION rather than inheriting it, decoding the live
  corpus's own c2s stream through `cmsgstream.timed` (per connection, so no
  interval is invented across a map load): at the 2026-08-19 calibration
  **2,789 retail self-reports, 2,747 intervals, ZERO on either arm**, fastest
  believable interval **388.80 u/s**, largest step inside 2.0 s
  **517.87 u / 1.352 s**, and below the dt floor -- the only place the distance
  arm ever fires -- a largest step of **19.15 u over 82 intervals**, which is
  27x of headroom. A constant justified in a comment is justified nowhere.
  **REPAIRED 2026-08-27, and the diagnosis had to come first.** The 2.0 s check
  was `abs(top2["dist"] - 517.87) < 0.05` and it went RED on `main` at
  **518.25 u** — the same shape as `test_itemmods` §10 and `test_adrenwire`, but
  NOT obviously so, because 520 is described as having been *chosen* from this
  very measurement, so a moved measurement could equally have been a movement
  regression with the threshold now wrong. It was not. Re-scanning the corpus
  **as of the pin** (stamps `< 20260820`) reproduces every frozen literal in §4
  to the decimal — 2,629 intervals inside 2.0 s, largest **517.87**, top speed
  **388.80**, **82** sub-floor rows topping at **19.15 u** — so the scorer had
  not drifted (`cmsgstream.py` is byte-identical since the pin, and `steps()`,
  `hard_step()` and every `HARD_JUMP_*` constant are untouched across the 2,000
  lines `movesync.py` gained). Seven new stamps carried it to 518.25, and
  **retail did not get faster**: the new stamps top out at **385.72 u/s**,
  *below* the old corpus's 388.80. 518.25 u / 1.352 s / 383.21 u/s is one more
  draw from the same ~1.35 s boost-cadence family that produced 517.87. The
  check is now a **floor** (>2,000 rows inside the window, because
  `max(..., default=0)` over an empty one clears a 520 u bar for free), a
  **relation** (the constant against the corpus's live extremum, reported with
  its headroom — 1.75 u today, and NOT physically bounded, since a 2.0 s gap at
  retail's own top speed reaches 778 u), and a **shoulder** check that
  disambiguates the two ways the relation can redden: *relation RED + shoulder
  RED* is one row standing alone above the walking cloud and belongs to REALFIX;
  *relation RED + shoulder GREEN* is the cloud itself drifting and means only
  that §4's decision record expired. Both were demonstrated by injection rather
  than argued — a lone **600 u / 1.6 s at 375 u/s** row (deliberately under the
  speed arm, so this window is the only thing that can see it) reddens both,
  while **40 rows at ~524 u / 1.80 s** at walking speed redden only the first.
  Four deliberate breaks, four correct signatures. Nine earlier sabotages were
  BUILT AND RUN and all nine redden,
  including reverting each arm separately, widening to the contaminated form,
  lowering 520 to 400, dropping the plane carry, restoring the early return at
  the interval floor, and silencing the threshold sweep or the reconciliation.
  **§17-§20 put movetap's and movesync's OWN `_selftest_*` sections into the
  suite**, which is where 130 checks written for the gatefire probe on
  2026-08-20 were not: both modules carry a module-level `--selftest`, and
  `run_suite.py` discovers `test_*.py` from DISK, so neither was ever invoked by
  it -- the same defect as a test missing from this file, which the tree has
  shipped three times (`test_pathmap.py`, `test_skillcast.py`,
  `test_textrec.py`). §17 wraps movetap's fence sections: the **50** AgTrack,
  gate-1 and history-node displacements re-derived from build 38797's own bytes
  (each expected
  encoding BUILT FROM the module constant, so a wrong constant produces bytes
  that are not at that VA), and the 13 refusal cases that keep a failed read
  from minting the `0` that means "the fence is shut". **28 → 44 on 2026-08-21
  with REALFIX-I1, and sixteen of them are the history chain the client's own
  match test walks**: the next pointer (`0x00605A5D` push-front AND
  `0x00605732`'s advance — both ends, so null-terminates is read twice), the
  time field the allocator writes from its argument (`0x00604DCC`, `mod=00`
  being the proof it is at +0x00), the four-dword point including the plane word
  (`0x00605A63`…`0x00605A75`), the 0x2C stride, the 256-node block cap, the
  5000 ms block recycle and the 2500 ms head-age rule. **Four of the sixteen
  REFUTE this tree's own committed comment**, which said only +0x00 and +0x04 of
  the AgTrack record were ever touched and that +0x18 was UNVERIFIED: the
  appender writes record +0x08…+0x18 every time it runs and the walker reads
  +0x08…+0x14 back as the polyline's FIRST vertex before it steps to the head.
  The bytes won and the comment was rewritten. **44 → 50 later the same day,
  after a verifier lane re-derived the layout and found the sentence beside the
  recycle pin naming the wrong node.** The existing pin encoded only the
  CONSTANT 5000 and left its operand free, so "recycled when its OLDEST node is
  more than 5000 ms old" printed inside a green `[PASS]` while `0x00604BFF`'s
  operand is `[eax+edi−0x28]` with `eax = count*0x2C` — index `count−1`, the
  block's NEWEST node. The five new cases pin that operand (encoded FROM
  `HIST_NODE_STRIDE`, so a belief in the oldest node writes `+4` and reddens)
  and the SEVER pass beside it — `0x00604C56` zeroing every `node+0x04` into the
  block, `0x00604CBB` doing the same for `record+0x04` across the array at
  `0x00604CC2`'s `0x1C` stride, bounded by `0x00604C49`'s block span. **That
  sever is the real reason a chain cannot dangle into a recycled block**, and
  this tree had never written it down: the landing argued safety from the 5 s
  bound it was misreading. Section 5 also now reads the COFF Characteristics
  word out of the pinned image, because `PTR_MAX`'s ceiling had been asserted
  from `0x0122` in prose and checked by nothing. **§17 also wraps
  `_selftest_chain` (45), which drives `history_chain` over a bytearray** — no
  client, no vault, no `ReadProcessMemory` — through a healthy 4-node walk and
  every way a chain can be wrong: a chain longer than N (`truncated:max-nodes`,
  keeping the N nodes it read), a head in the null-guard region, one above the
  LARGE_ADDRESS_AWARE ceiling (measured off Characteristics `0x0122`, not
  assumed at `0x7FFF0000`), an unaligned head, an unreadable node at position 0
  and at position 1, a cycle, and two torn-read signatures — a node NEWER than
  the node linking to it, and one dated more than `HIST_FUTURE_TOL_MS` into the
  future. **28 → 44 after a mutation lane opened 36 holes in this file and ten
  stayed green**, all of them in the same two families: a fixture that could not
  express the failure it named, and a guard sitting at a call site rather than
  on the behaviour. The ten new cases are a SHORT read (the `len(blk) <` half of
  the module's own refusal was unreachable — every fake memory returned either a
  full span or `None`, so zero-padding a partial transfer minted a vertex at the
  origin and reported `ok`); the SYNC copy's plane word against the `w` word
  beside it (the fixture agent had `plane = 0` and `w = 0`, so the two dwords
  were interchangeable — and that is the half of the pair grant #37 turns on;
  the agent now carries plane 19, w 77, async 3, all distinct); a legitimate
  allocation ABOVE the 2 GB line, because the old ceiling case planted its head
  AT `PTR_MAX` and therefore refused whatever the constant was; the RECYCLE
  hazard modelled end to end (a slot re-appended under the read carries the
  current world clock and is caught as `unread:node-time-inverted`, which is the
  only defence there is); the future tolerance pinned from BOTH sides on its
  real ground; `HIST_NODE_SPAN` pinned to `N_POINT + 16`; a control that
  rebinds the MODULE GLOBALS and calls `history_chain` without the argument; and
  six checks that read `print_hist_summary`'s and `chain_cost_line`'s OUTPUT
  back out of stdout. **The tolerance's stated ground was wrong and is
  corrected**: it read "world-0/world-1 clock skew", but `sample()` and the
  appender take `now` from the SAME slot (`0x00605893` / `0x006058A5` against
  `A_WORLD`), so that control had no referent. The real ground is read ordering
  — the clock is read before the nodes — and the constant is now
  `HIST_FUTURE_TOL_MS = 250` rather than 2500. **The gate is checked in both directions**: at exactly
  `sep = 250.0 u` no read is issued at all (asserted on the fixture's own read
  log, because the gate is a design requirement — eight unconditional node reads
  is ~+40% of a sample and would fight REALFIX-T3's residual budget), and
  `HIST_SEP_GATE < GATE1_CUT − GATE1_BAND` so no sample that could ever be
  classified `above` is skipped by it. **And the cost is MEASURED rather than
  argued**: the section drives the real `sample()` over a whole-sample fake
  memory whose only variable is where the ASYNC twin stands (100 u vs 4,000 u,
  same shipped gate, no flag) and counts the reads — **8 below the gate, 17 for
  a full 8-node walk, +112%**. REALFIX.md §2.4 argued the gate from "a full
  sample is ~20 ReadProcessMemory calls, so 8 node reads is ~+40%"; `sample()`
  issues **8**, so an ungated walk would roughly double it and the gate is more
  load-bearing than the design note claimed, not less. (That is a read count.
  The Hz cost is a different quantity, needs a client, and is what
  `movetap.chain_cost()` measures before every run for `main()` to print, via
  `chain_cost_line()` — which exists because the section-9 wiring row asks only
  whether `main()` CALLS `chain_cost`, and a mutation that kept the call, threw
  the result away and printed neither figure ran 206/206 green. There is now a
  row requiring `print(chain_cost_line(...))` and a check on what that string
  says.)
  **The point of the whole section is that
  a refused chain must never look like a short one**: "no node within
  MATCH_RADIUS of q" is the sentence that revives candidate B, and a torn read
  produces it for free. §18 wraps movetap's
  C2/C3/C6/C7/C8/C9 sections -- episodes (7), the flip denominator (8), gate 1's
  ASYNC twin and 0x005FF820's clamp (26), the two early-outs (11), the
  vocabulary (7). §19 wraps movesync's C4/C5/C9 -- the three-way jump tally
  (14), the appender witness (19), the two spellings (6), and `print_fence`'s
  own report (11). **Those two grew
  because a review found the new checks pinned the DICT and never the TEXT**,
  and the text is the artifact `PROBE-GATEFIRE.md` §6 quotes: swapping the
  printed `reachable` and `fenced` cells, hard-wiring the printed `unread` to 0,
  printing the unread label breakdown in the fenced row, DELETING the whole
  three-way table while keeping the tally and its refusal, hard-wiring arm (a)'s
  `witnessed` to 0, borrowing `judged` for arm (b)'s denominator, and deleting
  the arm-coverage and PARTIAL lines were **each fully green**. Both printers
  are now read back out of their own stdout (`read_back_three_way`,
  `read_back_witness`) and compared cell by cell against the dict behind them, a
  missing row arriving as an ABSENT KEY rather than a zero; the tally fixture is
  **2 / 5 / 1** so every permutation of the three cells is visible, and the
  witness fixture holds `judged` 8 against `reach_pairs` 7 so arm (b) borrowing
  arm (a)'s denominator cannot pass. Two more of the same family: the refusal
  bar is now computed by `unread_refuses` from `UNREAD_REFUSE_SHARE` alone
  (`unread * 4 >= n` was a second copy of the same constant, so setting the
  named one to 0.90 left the code refusing at 25% while the prose claimed 90%,
  green both ways -- it is exercised at 0.90 AND at 0.10 so the bar is pinned in
  both directions), and the sentinel check asserts the three `missing:*` names
  are DISTINCT, because the subset test alone passed when all three held the
  same string. **AND THEN THE SAME DEFECT WAS FOUND ONE ALTITUDE HIGHER:** the
  text was pinned at the FUNCTION while the operator reads the PIPELINE.
  Deleting the `print_appender_witness(pop, indent, name)` call from
  `print_fence` -- the only path `movesync.main()` takes -- left `--selftest` at
  49/49 and this file at 147/147 with the whole of C5 gone from the report, and
  six more `print_fence` branches judged ZERO rows in the entire suite (the
  PARTIAL line, the per-label share denominator, the `samples=` stream the
  production call actually uses, the population REFUSAL, the legacy NOTE's
  denominator, and `if rc: return rc` making that refusal swallow the tally and
  the witness beneath it -- the exact substitution C4 exists to undo). The new
  §19 section drives `print_fence` ITSELF on one fixture that takes the
  production path and the refusing path together -- `samples=` supplied, `have`
  6 of `total` 8, unread 2 of 6 over the 25% bar -- with every number distinct
  from the one a substitution would put in its place (50.0% over `have` against
  37.5% over `total`, 11 stream samples against 8 paired), the row counts
  asserted before anything is printed, the three sections asserted IN ORDER by
  their offsets in the output, and a mirror at `total` 7 with no unread row so
  neither the refusal nor the PARTIAL line can be a constant. Its thirteen
  mutations all redden a named check. **Two checks per section,
  never one**: the section's verdict, and the number of checks it EXECUTED
  against a floor read off a real green run, because a section whose fixtures
  stopped matching reports `bad = 0` over nothing at all and the verdict cannot
  tell that from a pass -- `test_codec.py`'s empty glob, one layer up. Each is
  then BROKEN on purpose and required to go red: `episodes` returning no runs,
  `count_flips` pinned at (0, 0), `GATE1_CUT` moved off the float the image
  holds, `EARLY_OUT_A_MODE` 9 -> 8, `test_would_run` counting `world1:append` as
  open, `classify_reach` calling every cell fenced, `state_fields` reading
  nothing, `REACH_ALIASES` emptied to the pre-C9 reader, and
  `print_appender_witness` silenced to a no-op -- which is the mutation that
  landed green in the round before this one. **§20 asks BOTH MODULES
  what sections they define** and requires every one to have been wrapped, with
  a planted section as its control, so one added tomorrow goes red here instead
  of being found missing in a week -- the both-directions rule
  `test_srclint.py` §7 applies to this file. It rules on the set `_wrap` filled
  as it RAN and not on the floor table, because a name can sit in a table while
  its call site is deleted, and a coverage check reading the table would then
  certify a section nobody ran -- the same defect one level up; deleting one
  `_wrap(...)` call is one of the eleven mutations, and it reddens. §20 also runs each module's whole `--selftest` (movesync
  **80**, movetap **250** — 231 until CANCELWALK-R5 added section 14) so the operator's pre-flight command cannot diverge
  from the
  suite, with a control per module that raises its `SELFTEST_FLOOR` above what a
  green run executes and requires the module to refuse itself. (Both numbers
  were stale in this entry until 2026-08-21 — it said 65 for movesync, which
  had been 80 for a day — and movetap's was never here at all. `movetap`'s
  moved 158 → **206** with REALFIX-I1: §5 28 → 44, §9's wiring table 22 → 25
  with the three rows that keep the chain walk's call sites alive (`chain_cost`
  priced, `print_hist_summary` called with its own three tallies, `hist_why`
  tallied at all), §12 7 → 8 with the check
  that `sample()` actually CALLS `history_chain` rather than splicing eight
  blank keys from nowhere, and the new §13 at 28. Read off the run:
  6+1+1+0+44+13+14+15+25+38+13+8+28. **Then 206 → 230 the same day**, after a
  verifier lane and a mutation lane: §3 1 → 2 (an AST guard refusing
  capstone/pefile/PIL/numpy — `import pefile` was planted at the top of
  `movetap.py` and the whole affected set stayed green, because both packages
  are installed on the machine that would have caught it), §5 44 → 50, §9
  25 → 26 (`main()` must PRINT the cost, not merely call `chain_cost` —
  those three rows were described as keeping the OUTPUT alive and they keep the
  CALL alive; three separate mutations gutted the printers at 206/206), and §13
  28 → 45. Read off the run: 6+1+2+0+50+13+14+15+26+38+13+8+45. (44 for an
  hour: the future-tolerance block's own first draft wrote every case as
  `HIST_FUTURE_TOL_MS ± 1`, so all three scaled with the constant and
  widening 250 back to 2500 ran green — the self-referential defect this
  round was closing, reproduced inside the fix for it. A FIXED 400 ms case
  pins it into [40, 400).) **movesync had no
  module-level floor until 2026-08-20**: its sections 8-10 carried a `_floor`
  each and its sections 1-7 -- the pre-probe guards the operator's pre-flight
  leans on -- carried none, so deleting section 2's only check took it from 38
  [PASS] to 37 with `--selftest` and this file both still exiting 0. It declares
  `SELFTEST_FLOOR = 65` now, measured off a green run (15 + 14 + 19 + 6 + 11),
  and the four `_selftest_*` sections return `(bad, ran)` so the total is summed
  from what they executed rather than counted from what they printed. **And the
  per-section floors were the same half-rule from the other side**: sections 8
  and 9 declared 8 and 9 while executing 14 and 14, so either could have lost
  six checks with its OWN floor silent, caught only by the total and by this
  file's table -- two external nets under a number the section owns. Every
  `_floor` is now the count its section executes, instrumented rather than
  counted by hand, and dropping one check from section 8 or 9 reddens that
  section's own floor line as well as this file's. And it
  cross-checks every self-reporting section's returned count against the
  [PASS]/[FAIL] lines it printed, because **the first version of §17 was itself
  the defect it now guards**: it compared a section's `(bad, ran)` tuple against
  `0` -- which cannot be true -- and then compared the same tuple with `>`,
  which raised, so 16 green sections were followed by a TypeError and one check
  that could never pass. **§21 IS THE CLOCK ANCHOR, REALFIX-T1/T2, added
  2026-08-21, and its subject is that the two estimators are NEVER MIXED and
  that the file SAYS which one it used** — a run that silently fell back to the
  truncated `wall` stamp produces identical-looking numbers everywhere
  downstream, which is how a 1.00 s error survived two whole analysis lanes.
  `authsrv.Recorder.event` now stamps `wall_unix` beside `wall`, and
  `movesync.offset_detail` prefers it (median over per-row offsets, spread as
  the residual) or falls back to the truncated max-estimator (offset from below,
  ~1 s residual by construction) — one family or the other, with `n` against
  `n_trunc` naming a mixed file rather than averaging it into a number that is
  neither. It is demonstrated THREE ways and the third is the one that carries:
  a synthetic post-T1 capture (offset exact to the microsecond), a synthetic
  pre-T1 one at **0.977 s / 281 u** — 40 rows at a 0.317 s cadence, because six
  rows reach only 0.76 and would have understated the defect — and then
  **`authsrv.Recorder` ITSELF, in process, writing 201 real rows**: spread
  **12–32 µs = 0.004–0.009 u across runs**, against REALFIX §2.2's
  "< 1 ms (< 0.3 u)" clock term, measured on the same two adjacent clock reads a
  live run makes rather than on a fixture whose stamps are exact by
  construction. (This entry said "200 rows, 11.4 µs" until 2026-08-21. The row
  count was off by one — the origin row `Recorder.__init__` emits is included,
  and the test asserts `n == len(reports) + 1` — and the µs figure is a single
  draw from live scheduling jitter that re-runs at 12.4, 14.3 and 31.7. The
  claim §2.2 needs survives by ~30× on the worst draw; the point estimate does
  not, so the range is quoted.) **The float arm's MEDIAN now has its own
  control**: one 5 s outlier in 40 rows, which moves a mean 125 ms = 36 u and
  the median not at all. The truncated arm's max-estimator was well guarded and
  the float arm's median was not, because every other fixture here is exact by
  construction and mean == median in all of them. **And both source greps in
  this section now run over LIVE lines**: commenting out
  `kw["wall_unix"] = time.time()` left them green (the behavioural checks caught
  it, which is why this is a hardening rather than a hole). `offset_from_stamps` keeps
  its two-value return (`pair`, `resyncscore`, `grantsim` and this file's own §1
  all unpack exactly two) and `WallStamps` subclasses `list`, so
  `getattr(walls, "unix", ())` IS the fallback test and a hand-built list of
  floats still works — there is no version flag to get wrong. Floor **127**, the
  bare-machine subset, against a green **177** with every capture present;
  §11-§16 declare `LEDGER.skip` without
  them, and so does `movetap._selftest_fence_bytes` (that section's two checks
  and its one control are the only 3 of §17-§21's 70 that need the vault's
  client snapshot; the other 67 run on a bare machine). **§17 also wraps
  `movetap._selftest_chain`, REALFIX-I1**, with three controls that each redden
  it: `HIST_SEP_GATE` raised past every fixture (which is what a gate quietly
  set too high does to a whole live run — the chain is never read and the file
  looks healthy), `HIST_MAX_NODES` cut to 2 (a walk that called a truncated
  chain `ok` would licence a null over a polyline it never finished reading),
  and `PTR_MIN` dropped to 0 (a head inside the 64 KB null-guard region reading
  as an address). **This entry used to say those controls are why
  `history_chain` resolves both parameters in its BODY. They are not**, and a
  mutation proved it: all three pass the parameters explicitly, so moving the
  defaults back into the signature left both this file at 174 and
  `--selftest` at 206 green. The mechanism is real — rebinding a module global
  is silently ignored under a signature default — and the control that actually
  proves it now lives in `movetap._selftest_chain`, which moves
  `HIST_MAX_NODES` and `HIST_SEP_GATE` on the module and calls without the
  argument. **§17 also wraps `movetap._selftest_r5` (9), CANCELWALK-R5's
  decode-only field set** — `+0x50` the MOVE-REQUEST CORRELATION TOKEN the
  local applier allocates per successful walk-start call (**this entry and the
  code both called it a "planner" for one day; the read that corrected it is
  `studies/movement/CANCELWALK.md` §7.4d — nothing in the image branches on
  the field, so `0 → N` is a walk-start DETECTOR and never a cause**),
  `+0xBC/+0xC0` the facing pair, plus raw stop/point/velocity, on BOTH world
  copies, all decoded from bytes the poll already fetches (zero new
  cross-process reads). Two controls redden it,
  and they guard the failure mode that would VOID the run rather than break
  it: `A_REQ_TOKEN` slipped one dword to `0x54` and `A_DIR` pointed at `0xC4`
  (the movement mode, an int) each return confident numbers that never
  change — which reads as "the walk-start never ran", so a wrong offset would
  be indistinguishable from a real freeze. The section also asserts the ASYNC copy
  surfaces its own values rather than a second decode of the sync block (the
  one substitution that makes the whole readout meaningless) and that a
  refused twin read blanks every async key instead of leaving the previous
  row's numbers standing. Landing it also earned §20's uniqueness check its
  keep: R5's `stop` key collided with the one `sample()` already ships from
  the same offset, where `**` would have let the splice silently win. The row
  key is `reqtoken`/`async_reqtoken`; capture `movetap-20260824T141620`
  predates the rename and carries the old `planner` spelling.
  **§21 also guards both modules' import lists** (`movetap.py` and
  `movesync.py`, asked of the syntax tree), a second witness beside movetap's
  own §3 so the guard cannot be deleted from one place quietly. No client. ~4 s),
  `toolkit/clientscan/test_resyncscore.py` (WHAT WOULD THE 0x002C RESYNC HAVE
  DONE -- the guard on `toolkit/clientscan/resyncscore.py`, which prices a
  server change nobody has made against captures already on disk. The proposal:
  `GAME_SMSG 0x002C AGENT_UPDATE_POSITION` is the one catalogued primitive whose
  handler (`0x005FDA50`) calls `AgTrack::Clear` FIRST (`0x005FDA78`) and then
  SetPositions **both** agent arrays with no gate on either arm, so it is the
  only message that can reach the copy the player actually sees once
  `0x0025`'s async arm has been gated shut for the client-controlled agent. The
  scorer reuses `movesync`'s loaders and its repaired two-arm hard bar verbatim
  -- `load_wire_reports`, `load_grants`, `steps`, `hard_step`, `on_segment`,
  `denominator`, `per_minute` -- and adds no decoder of its own, because a
  second reader is a second chance to disagree about what the client said.
  **A counterfactual has three ways to lie and there is a section for each.**
  §0 (added by the 2026-08-25 reconciliation) pins the ONE threshold: this
  file's `RESYNC_SEPARATION` equals `authsrv.py`'s equals 100.0, GATE1_UNITS
  stays the measured client constant above it, and THRESH_SWEEP prices the
  shipped cell -- until the reconciliation the tool's default was the fence
  (299.33) and every bare invocation priced a rule the server does not run.
  §15 is the load-bearing one: ArenaNet's own traffic scores **0 hard jumps**
  over 35 usable game connections and 2,739 self-reports, so a rule that fires
  on retail as often as on our defective build is reading the wire, not the
  defect -- and it **currently fails for two of the five rules**, which is
  PINNED rather than tolerated. At the shipped 100.0 cell (re-measured
  2026-08-25; the fence-cell figures of 4.13x/0.816x/0.024x/0.026x/0.228x
  stand as the 2026-08-20 write-up's): Rule C (`0x002C` before every player
  grant) fires **4.54x more per minute on retail than on the build we ship**;
  Rule D (C plus an arrival model on the previous leg) fires 1.50x. Rules A
  and B separate at 0.036x and 0.028x, and **Rule E -- a forward model of the
  sync copy -- gets both halves: 7 of 7 covered at 0.345x**. A session that
  "improves" C without re-running the control turns §15 red, and moving the
  comparison's reference from the SHIPPED build to our worst capture -- which
  makes C read as 0.101x and "separating" -- reddens six checks. **§18 is the
  check that can refute Rule E**, and it is the only claim in this file that is
  not about this file: a forward model is the "four assumptions stacked under a
  conclusion" `movesync.py`'s header refuses, so it is paired against
  `movetap-20260819T145939`, a `ReadProcessMemory` of `[agentMgr+0xE8]` in the
  session capture `20260819T145717` recorded. The model sits **p50 0.0 u, max
  67 u from what the client's own memory held over n = 251**, and the separation
  it computes from grants on the wire reproduces `studies/movement/HANDOFF.md`
  §1's **1,164 / 2,163 / 3,648 u** exactly, by a path that never opens the
  movetap file to compute them. That section carries its own positive control,
  which mutation put there: hard-wiring the residual to 0.0 left it green, so
  the model is now deliberately halved in speed and the same residual must move
  (0.0 -> 202 u over the same 251 pairs), and pairing a movetap run from a
  DIFFERENT session must return None rather than inventing a comfortable row.
  **§17 prices every threshold in the file**: retail's own two copies, through
  the same model, sit **p50 83 u, p75 260 u, p90 653 u** apart with zero snaps,
  so a resync threshold of 100 u sits at ArenaNet's MEDIAN separation while our
  shipped build sits 13.5x further out. **§19 is the actionable half**: the
  COOLDOWN is where the coverage goes, not the threshold -- Rule E covers 7/7 at
  cooldown 0.00 s, 3/7 at 0.50 s and 2/7 at 2.50 s, while the yank stays p50
  0.08 u at all three, because the payload is always the client's freshest
  adopted report; and the shipped 100 u cell holds the fence cell's 7/7
  coverage at 31 extra firings on the shipped capture (restated 2026-08-25
  from "dropping to 100 buys no coverage" -- the default IS 100 now, and the
  corpus gains a covered jump there: §13's second table, `182652` 13 vs 12).
  §1-§2 pin `leg_distance` as the SEGMENT
  distance and prove it is a lower bound on separation against a 201-position
  sweep of the granted leg, the row count asserted first. §3 gates the arrival
  model in both directions on a 2,000 u leg (t_park = 6.944 s): 32 firings, none
  before it. §4 requires Rule B to fire **0 times** on a client walking the leg
  it was granted and 25 times on one walking perpendicular to it -- without the
  second half the first passes for a rule that never fires. §5 pins D as a
  structural SUBSET of C **and** shows D firing once on a leg that did finish,
  because a subset relation is free for a rule whose gate is `return False`.
  §6-§7 pin the cooldown's bound on the inter-firing gap and the threshold's
  monotonicity. §8-§9 are the COST, in the units the harm arrives in: the
  payload is `state["pos"]`, so **staleness is non-zero only where the
  position-trust guard REFUSED a report** (3 consecutive refusals leave the
  payload 216 u = three intervals behind, and the tool names the one-line
  mitigation beside it), and the self-mint bar is asserted to BE
  `movesync.HARD_JUMP_UNITS` by identity rather than by value -- a private copy
  is how a fix ends up scored on a friendlier bar than the defect it replaces.
  §10 pins coverage to the interval a firing lands in and mutates it in-process
  by deleting that firing. §11 exercises the refusals: an unknown rule name, a
  capture with no player grant declaring a NULL **with its reason** instead of a
  bare 0, and the retail control over ZERO connections REFUSING rather than
  returning a comfortable zero -- `all([])` is True and this repo has already
  shipped that control once. §11b pins the sync model's shape before any capture
  touches it: seeded at the client's first report, still gliding 0.25 s short of
  a 10.000 s leg (the negative half, so a model that teleports on the first tick
  cannot pass), PARKED at t=12.0 s and t=14.5 s, and re-aimed by a fresh grant
  from where the MODEL has it rather than from the client's report -- which is
  what the client's own bake does, reading the sync agent's `+0x78`.
  §13 pins the vault replay cell by cell at BOTH threshold cells, 30 cells
  since 2026-08-25: the FENCE cell (299.33, named explicitly -- the 2026-08-20
  write-up's numbers, no longer the default) reads `20260819T145717`
  116/85/38/4/213 firings and 3/1/5/2/7 covered of 7 for rules A/B/C/D/E,
  `171153` 1/7/702/1/66, `182652` 0/3/318/0/40; the SHIPPED cell (100.0,
  measured 2026-08-25) reads 117/154/39/4/244, 2/11/726/2/234 and
  1/5/320/1/110 -- where Rule E covers **13 of 13** on `182652` against the
  fence's 12, the row that shows "raising costs no coverage" was true of one
  capture and not the corpus. It also
  re-measures the
  census -- **0 x 0x002C sent, every run** (true of these 2026-08-19
  captures; corpus-wide the claim died 2026-08-20 with the `--resync` run's
  18 sends, joined by the pin's 6 -- total 24) -- and pins
  THE FINDING: all four
  jumps Rule A cannot reach are missed for `not-parked`, i.e. blocked by the
  arrival model rather than by a threshold or a cooldown, so **no parameter
  reaches them**. §14 exists because the prompt this arc was handed called
  `20260811T173940` a retail capture: `origin.origin_of` says `ours`, build
  38797, in `captures/gamesrv/`, with 0 player grants and 0 hard jumps -- an
  internal null, and a consistency check on both halves. It also proves
  `require_single_origin` refuses a run pooling `ours` with `live`, which each
  file's own per-file check cannot catch. §16 resolves the retail player agent
  from that connection's own `0x0037` and corroborates it with the id-free
  signature the 2026-08-19 corpus pass used, |grant dest - the client's own
  report|: over the 20 connections with **>= 5 rival agents** the named agent
  beats the population median every time (margin 1.12x worst, 4.43x median),
  and the nearest-rival form -- which separates on only 25 of 35, because a
  henchman a step behind the player looks like the player -- is MEASURED and
  deliberately not the check. The population floor is declared rather than
  chosen after seeing which rows pass, and the one connection it excludes is
  named. **Sixteen mutations were built and run and all sixteen redden**:
  dropping `leg_distance`'s clamp, removing Rule A's park gate, unbinding the
  cooldown, swapping the self-mint bar for a private constant, letting the
  payload ignore whether a report was adopted, picking the retail player by
  grant volume instead of `0x0037`, deleting the empty-population refusal,
  making coverage count a jump whenever any firing happened, scoring the null
  capture as a plain zero, moving the discrimination reference off the shipped
  build, and six on the model: never parking, teleporting to the destination on
  the grant, re-aiming from the client's report instead of its own state,
  running at half speed, comparing the model against ITSELF, and returning a
  comfortable row where it should return None. **The last two were HOLES the
  first pass left** -- a residual hard-wired to 0.0 and a refusal path no
  full-vault run ever reaches -- and both are what the positive controls in §18
  now exist for. Floor **47**, the bare-machine subset, against a green **98**
  with the vault present; §13-§14, §15-§17 and §18-§19 declare `LEDGER.skip` in
  groups without `captures/gamesrv`, `captures/live` and `captures/movetap`.
  Reads only; sends nothing, and never imports `authsrv.py`. No client. ~6 s),
  `toolkit/clientscan/test_grantsuppress.py` (WHAT WOULD SUPPRESSING THE GRANT
  HAVE DONE -- the guard on `toolkit/clientscan/grantsuppress.py`, which replays
  `authsrv.py`'s `GRANT_SUPPRESS` rule against the captures from the owner's own
  2026-08-20 session BEFORE the reproduction is played again. Where
  `resyncscore` prices an ADDITIVE fix (send a `0x002C` we never send), this
  prices the SUBTRACTION, and its spine is a stream neither of the other two
  loads: the c2s control traffic (`0x003D` with its `movementType`, `0x0047`,
  `0x003E`) that says whether the player's hands were on the keyboard when we
  granted. It reuses `movesync`'s loaders and its repaired two-arm hard bar
  verbatim and defines no bar of its own -- §3 asserts that BY IDENTITY, and by
  the absence of `hard_step`/`HARD_JUMP_*` from the file's own text, because a
  private copy is how a fix gets scored on a friendlier bar than the defect.
  **THE HEADLINE, and its honest half.** On the reproduction
  `authsrv-20260820T183311-c1` (196 clicks, 140 grants, 44 s, 5 hard jumps at
  p50 1,372 u / max 3,010 u / 6.82 per minute of span) the keyboard arm
  suppresses **140 of 140** -- every grant went out while the client was
  backpedalling under its own control -- and the counterfactual removes **5 of
  5** hard jumps. On the capture of the build we actually ship,
  `20260819T145717`, the same rule removes only **2-3 of 7**: 2 plausibly kept
  because a causal grant survives it, and 2-3 UNATTRIBUTED with no grant in the
  causal set at all. §14 pins that row as the load-bearing one, because 5-of-5
  is a statement about that session and not about the build.
  **§12 IS THE SECTION THAT REFUSES THE COMFORTABLE NUMBER.** "4 of the 5 jumps
  had a grant inside 0.5 s" is true and very nearly free: grants arrive every
  0.150 s in that storm, so **83 of the capture's own 132 report instants (63%)
  also have one**, and the jumps beat their own baseline by 17 points over
  n = 5. The rotation control -- jump times moved, grant train untouched --
  still scores **18/27 = 67%**. So on the reproduction the time arm is grant
  DENSITY and the file says so ABOVE the count. `20260819T145717`, whose
  baseline is 10%, is where that arm carries information (43% vs 10%, rotations
  0-2 of 7). **§13 is what does discriminate, and it is the fifth jump**: the
  one with no grant inside 0.5 s landed **0.000 u -- bit-identical -- on a point
  granted 5.07 s earlier**, against a control (nearest place the client had
  already stood) of 1,105 u. It is not unexplained; it is the `+0x48` arrival
  maturing, which a 0.5 s lookback cannot see by construction, and 2 of the 5
  landings are bit-exact on a granted point. The counterfactual is therefore
  printed as a **BRACKET** across two attributions (a 50 u display band, and a
  parameter-free "closer to a granted point than to anywhere it had already
  stood") rather than at either alone, and §6 asserts the four buckets --
  removed / kept / unattributed / **unknown** -- PARTITION on every capture. The
  fourth exists because `sup_at.get(t, False)` would score a lookup MISS as
  "the rule keeps it", which reads as a finding when the truth is that the code
  could not tell. **THE CONTROLS, and the reason there are two kinds.** Tonight's
  other two captures carry **ZERO grants**, so a suppression share over them is
  0/0 and §7 pins that the tool REFUSES it by name and returns non-zero rather
  than printing a comfortable "0 of 0". The control with a denominator is §8:
  the **five clicks** in `20260820T182934`, of which the rule calls **0**
  keyboard-driving at every W in the sweep, against 196 of 196 in the
  reproduction -- the same classifier, the opposite answer. §9 is the mutation
  that proves it can fail: delete the stop term and 182934 goes 0/5 -> 1/5 at
  W=1.0 and 0/5 -> 2/5 at the shipped W=3.0, and the stop term keeps 10 of
  `145717`'s 40 grants. §10 is the classifier's POSITIVE control and it prices
  the rule's only free parameter against the client's own cadence: a straight
  keyboard hold in `20260820T182554` reports every **1.80-1.82 s**, so W = 1.0
  -- `authsrv.py`'s own `fresh` constant, and the number a reviewer reaches for
  -- leaves **10 of that capture's 15 intra-hold intervals uncovered**, which is
  grant-shaped leakage in exactly the posture the owner is most likely to try
  next; at 2.0 and at the shipped 3.0 it is 0 of 15, and the classifier calls
  87% of that capture's span driving against 56% of the click-only one.
  **§15 pins the two arms MARGINALLY and mirrors the server's own constants.**
  Behind the keyboard arm the rate limit removes nothing MORE, which reads as
  "it does nothing" and would get it deleted; ALONE it takes the reproduction
  from 140 grants to **38** (102 suppressed) -- independently reproducing the
  figure `authsrv.py`'s own comment carries. The rate arm is asserted to be a
  STATE MACHINE and not a pairwise filter (102 vs 134 over the same timestamps,
  because a suppressed grant does not reset the floor). `GRANT_LOCAL_WINDOW`,
  `GRANT_MIN_INTERVAL` and `GRANT_SUPPRESS` are read out of `authsrv.py`'s
  SOURCE TEXT -- never imported, that is a server module -- and pinned against
  this file's mirrors, so a retune reddens here and whoever retunes re-runs the
  replay; every number above is a number FOR THOSE VALUES, and the flag is
  asserted OFF by default so this is a costing of an OPT-IN. The headline is
  also asserted identical at this file's independently derived W = 2.0, sized
  from a different corpus filter (74 captures, 4,190 intra-hold gaps, 96.25%
  at or under 2.00 s) than the server's 3.0. **Nine mutations were built and
  run and all nine redden**: deleting the stop term, deleting the recency term,
  letting a missing suppression key score as `kept`, scoring the density null
  over the jumps instead of the population, attributing by time only, making the
  rate arm pairwise, drifting either shipped-constant mirror, and turning the
  0/0 refusal into a plain zero -- with the source sha256 asserted identical
  before and after. Floor **29**, the bare-machine subset, against a green
  **85** with `captures/gamesrv` present; §7-§15 declare one `LEDGER.skip`
  without it. Reads only; sends nothing, and never imports `authsrv.py`. No
  client. ~7 s),
  `toolkit/clientscan/test_gatetrace.py` (**A WRONG ADDRESS HERE DOES NOT
  ERROR -- IT RETURNS THE FINDING.** The guard on
  `toolkit/clientscan/gatetrace.py`, CANCELWALK-R7, which attaches a 64-bit
  debugger to the loopback client, arms Dr0-Dr3 in the NATIVE context, and
  reads the local walk-start applier's two gate operands
  (`[controller+0x10C]`, `byte[+0x64]`) at the instant a movement key is
  pressed. **§1 is the section that carries the file**: reading one dword away
  returns a confident value that never changes, which is exactly what
  "the walk-start never ran" looks like and would be indistinguishable from
  R7's own hypothesis -- so the expected instruction bytes are **ENCODED FROM
  the module constants** and matched against the pinned image (`OFF_STATUS`
  builds `8b 83 <disp32>`, `BIT_GATE_A` builds `a9 <imm32>`, `OFF_FLAGBYTE`
  and `BIT_GATE_B` together build `f6 43 64 01`, `BIT_GATE_C`'s bit index
  builds `shr eax,4`), with a control that moves `OFF_STATUS` to `0x110` and
  requires the match to break. Comparing a literal to a copy of itself would
  pass forever. **AND UNTIL 2026-08-30 ALL OF THAT GUARDED THE WRONG
  CONSTANTS**, found while paying the build-pin census bill: `buildpins.py
  --live` charges `gatetrace.py` four pins -- `VA_APPLIER`, `VA_GATE_BAIL`,
  `VA_NAVMESH_EXIT`, `BUILD` -- and §1 touched none of them. The four derived
  rows above read their ADDRESSES from literals typed in the test
  (`0x0081A925/931/93C/946`); the three rows that did use the counted VAs had
  HAND-TYPED patterns -- `55 8b ec`, `ff 73 14`, `5f 5e 33 c0` -- occurring
  **14,765, 94 and 531 times in `.text`**; and the control moved `OFF_STATUS`,
  which is real but is not a pin. MEASURED: point all three VAs at decoys four
  megabytes away and the section printed **9 of 9 PASS** under a line reading
  "the byte checks above are load-bearing". The repair is three-part and each
  part is separately checkable. (i) The four derived rows are now written as
  `VA_APPLIER + 0x35/0x41/0x4C/0x56`, so the pin carries five rows instead of
  none -- and that takes five class-(c) occurrences (four distinct addresses)
  back out of the file, net minus three across the tree once the two call
  targets below are counted in. (ii) The
  three VA patterns are widened until each **occurs exactly once in `.text`**
  (30, 8 and 21 bytes), which the section RE-MEASURES every run and prints, so
  a pattern that stops identifying reddens rather than being asserted in a
  comment; two of them assemble their `e8 <rel32>` FROM the VA under test
  (`0x005FCA80` for the bail, `__security_check_cookie` for the exit), making
  those rows position-DEPENDENT -- the same bytes read elsewhere decode to a
  different callee -- and the exit's `ret` imm16 is built from `ARG_MT_ESP_OFF`,
  which is not a coincidence to be tidied away: four dword args is why `mt` sits
  at `[esp+0x10]`. `55 8b ec` needed widening past 24 bytes because the first 24
  still match TWO functions (`0x00754EF0` is a near-twin: same `0xC0` frame,
  same cookie load). (iii) Four controls, **one per counted pin**: each VA is
  moved to another of the three and every row resting on it is required to go
  red, and `BUILD` is exercised by reading every OTHER vaulted build through
  the same `pinned.find` and requiring every row to fail there (it does, on
  38519, 38833 and 38849). §1 also RESOLVES ITS IMAGE through
  `pinned.find(gatetrace.BUILD)` now instead of `os.path.join(root, "client",
  "2026-07-29_221c13772c7a", "Gw.exe")` under an `os.path.exists`: `BUILD` was
  read by nothing at all (`git grep gatetrace.BUILD` empty, against six for the
  positive control `git grep atex.TABLES_BUILD`), so bumping it for a rebase
  moved nothing and the guard could never be aimed at the newer image it exists
  to redden against -- `atex.TABLES_BUILD`'s own fix, one build later, and
  `find()` additionally hashes what it returns where `os.path.exists` cannot.
  The two failure modes are kept apart on purpose: a `BUILD` the registry does
  not know is **this file's bug and a FAIL**, while a known build absent from
  this machine's vault is a bare machine and a SKIP. An unplanned dividend,
  MEASURED: the applier's 30-byte pattern is unique in the newer builds too
  (`0x0081A940` on 38833, `0x0081A9C0` on 38849) and with `VA_APPLIER` moved
  there all four gate rows match at the same offsets, with both exits still at
  `+0x41F` and `+0x40A` byte for byte apart from their two rel32 displacements
  -- so the function relocated as a unit twice and the pattern doubles as the
  rebase instrument. §2 drives all eight operand combinations and asserts the bail
  list is in the client's own **test order** A,B,C -- a set would lose the only
  thing that explains the frame -- and that an unread operand yields no verdict
  rather than a plausible "no gates set". **§3 proves the file can contradict
  itself**: the entry read predicts an exit and the exit breakpoints observe
  one, so all three disagreement shapes are asserted to report `agrees=False`
  loudly; a tool that could only agree with itself would be worthless. §4
  enforces the control rule this route earned in `debugread.py` -- no
  `PeekMessageW` hit is **rc 2 VOID, never a null**, because silence is this
  route's own known failure mode (a WOW64 vectored handler never receives the
  exception). §5 checks the ASLR math and that the three watched addresses are
  distinct (two Dr slots on one address silently halves the trace). §6 bans
  `WriteProcessMemory`/`VirtualProtectEx`/`CreateRemoteThread`/`VirtualAllocEx`
  by name -- the whole licence for pointing this at a running client is that it
  only reads. **§6 ALSO CHECKS THAT THE TOOL REFUSES TO RUN, by calling
  `trace()` and requiring it to raise**: an adversarial review measured five
  blockers in the process half on a real WOW64 target, the first of which kills
  the client on the first breakpoint hit (it dispatches on
  `EXCEPTION_SINGLE_STEP` where a 64-bit debugger attached to a WOW64 target
  receives `STATUS_WX86_SINGLE_STEP` 0x4000001E -- a constant
  `commandertrap.py` in the same directory already defines, with a header
  explaining this exact failure). The refusal names both the blocker and the
  poll that replaces it, because a docstring warning above a `main()` that
  still runs is a file that gets run. Floor **35**, the BARE-MACHINE number; a
  machine with the pinned snapshot executes 51 (44 before 2026-08-30, and 50
  where the vault holds no build but the pinned one, the `BUILD` control
  declaring a skip instead). **That floor was wrong until
  the same review caught it**: it declared 42 with §1 calling
  `LEDGER.skip(..., 9)` in the belief that a skip lowers the floor by its
  count -- `Ledger.skip(label, why)` takes two strings and lowers nothing, so
  the file was RED on any machine without the vault snapshot while five
  documents claimed it dropped to 33. No client needed. ~1 s),
  `toolkit/clientscan/test_policyreplay.py` (the offline policy bench,
  RETHINK instrument #3 — the promoted form of the scratchpad sim whose one
  offline counterfactual (the sec.0.16 literal candidate: 2 of 24 fires
  survive) out-earned every live refutation that week. Guards
  `toolkit/clientscan/policyreplay.py`: the engine's cells on a synthetic
  log authored to the shipped semantics (fire / rate-hold-then-expire at
  held+1.0 s exactly / late-fire off the flush after an `0x0047` that
  clears WITHOUT voiding / `0x003D` void / newest-wins overwrite / the
  shared grant clock a zero-lead fire advances / the geometry-flag
  pairing), the FIDELITY GATE passing there and on BOTH real 2026-08-26
  logs under the policies they actually shipped with (113824+sec015:
  24 fires, 7 expiries; 143111+sec017: 64 fires, 9 expiries — **a PASS
  that required modelling the geometry branch's `state["dest"]=None`
  clear at authsrv :15853, a shipped-code fact the gate itself DISCOVERED:
  the sec.0.17 leg bound is void for every geometry-flagged click, 126 of
  the P-17 log's 179**), the gate going RED under a perturbed rate floor
  (a gate that cannot fail is not a gate — grantsim's C3 lesson) and under
  the wrong policy, and the negative control: bare-hold still suppresses
  22 of 24 on 113824, the number that killed it. NEVER a ranker, by the
  same C5 discipline as its neighbor below. Synthetic section bare-machine;
  real-log sections skip loudly. Floor 14 from the green run — the header
  records its own head-count-vs-run defect (declared 16, ran 14). ~15 s),
  `toolkit/clientscan/test_grantsim.py` (**WOULD A DIFFERENT GRANT POLICY HAVE
  SNAPPED -- AND THE ANSWER IS THAT THIS FILE CANNOT TELL YOU, ON PURPOSE.** The
  guard on `toolkit/clientscan/grantsim.py`, which replays a capture's own c2s
  `0x003D`/`0x003E`/`0x0047` through each candidate policy, drives a byte-exact
  rebuild of the client's `0x005FE950` bake, and asks the client's own question
  at the client's own two caller classes. Where `resyncscore` prices an ADDITIVE
  fix and `grantsuppress` prices the SUBTRACTION, this prices a SUBSTITUTION.
  **IT IS NOT A RANKER AND ITS TESTS REFUSE TO LET IT BECOME ONE.** §8 sweeps the
  match test's PRESENCE alongside its radius over 54 cells, because that is the
  axis where the ranking inverts: with the match test on, leads 0 u and 86 u
  score identically on three of four counterfactual captures (0/0, 0/0, 2/2,
  3/2) and only the already-refuted 766 u lead separates -- **it is worst in 27
  of 27 cells** -- while with the match test off it **WINS in 27 of 27** (2 vs 10
  on `20260820T182554`, 21 vs 23 on `182934`, 29 vs 48 on `20260814T100340`).
  `rank_or_refuse()` therefore returns None on the real substrate and §8 asserts
  BOTH directions, refusing on an inverting band and still producing an ordering
  on a synthetic invariant one, so the refusal is a measurement rather than a
  function that always says no. **THE HEADLINE IS THE CALIBRATION.** §5
  reproduces the measured hard-jump census on eleven `ours` captures across five
  configurations -- 60 measured, 69 predicted, 1.15x -- and, the check that
  separates this from its own first draft, **exactly zero** on the three
  captures that sent zero grants, where round 5's separation-only scorer
  predicted 16, 12 and 34 because `20260819T145717`'s real separation is p50
  1,164 u with 7 jumps in 320 s. §5 asserts a **committed per-capture
  expected-count vector** rather than a ratio band, because two independent
  implementations of the same written specification gave 69 and 80 against that
  60; committing a capture is refused (the vault stays local), so the fixture is
  split -- a SYNTHETIC minimal capture this file builds carries the structural
  behaviour and the vector is NUMBERS ONLY, keyed by stamp, and is recorded as
  **IMPLEMENTATION-PINNED**: it is what this code does, not what the spec
  entails. **§7 IS WHERE IT ADMITS WHAT IT CANNOT SEE:** deleting the match test
  takes 69 to 122 (1.77x) and rotating destinations inflates it monotonically
  (69/73/99/133 at k = 0/1/5/17), but shifting every grant by +0.35 s --
  destroying causality outright, below the 0.490 s inter-grant median -- scores
  **60, dead on the measured total**, so the shift null is gated per capture at
  +3.0 s only (`195137` 8 -> 0 against a measured 8, `182652` 12 -> 5 against 13)
  and the +0.35 s failure is PRINTED. At matched perturbation scale the file is
  no more geometry-sensitive than cadence-sensitive -- rotate-1 +5.8% against
  shift-(-0.35 s) +10.1%, asserted to stay inside one order of each other so the
  manufactured asymmetry cannot come back. **§6 RUNS THE SERVER'S OWN
  PREDICATE**, and it is the one place this file breaks its neighbours' rule:
  `grantsim.py` imports `authsrv.py` (lazily, first use only) rather than
  mirroring its constants out of the source text, because `_grant_verdict`'s own
  docstring says it was made side-effect-free so an offline scorer could run the
  decision rather than a paraphrase that agrees with it by construction.
  `20260820T195137`'s **199** `grant_verdict` rows (all `off`) and
  `20260820T195315`'s **154** (**152 `locally-moving` + 2 `grant`**) are
  reproduced exactly, reason for reason, against the 199 and 2 `0x0029` those
  captures actually put on the wire, with the replayed `keyboard_age` agreeing
  numerically to **0.59 ms**; the NEGATIVE CONTROL replays `195315` with the flag
  the other way round and must reproduce **nothing at all**, 0 of 154. It is
  labelled **§6 C3 (click-arm)**, and its heading half is **§6b** -- see below.
  Until 2026-08-21 that half was a `LEDGER.skip` naming a symbol `authsrv.py`
  did not have; `_heading_grant_ok` landed that day, so P2 and P3 are no longer
  scored with no rate limit at all. **§3 IS THE
  CONSTANT NOBODY HAD DERIVED:** the match test's effective threshold is not the
  `100.0f` the client compares against, because the comparison runs through the
  table sqrt at `0x0046E870`, so §3 re-reads the 256-dword LUT with a stdlib PE
  walk and scans **all 2,048,001 float patterns in [9000, 11000]** to put the
  boundary at `9984.0f` = **99.919968 u** -- with gate 1 as the positive
  control, the identical scan over a different 2,560,001-pattern window
  reproducing `89600.0f` = **299.332591 u** and settling that a true separation
  of exactly **300.0 u SNAPS**. Both module constants are then asserted against
  their own derivations, because a constant that has drifted from the function
  that produced it is the defect the section exists for. **§4 GATES ON THE
  GLIDE-CONDITIONED RESIDUAL**, from the two high-grant movetap pairs only
  (`152716` p50 20.68 u, `171153` 14.62 u, both max under 61 u against a 99.92 u
  decision radius), because three of the five pairs are 53-83% parked and their
  unconditioned p50 of 0.00 measures the parking, not the model -- those three
  are reported, and their parked fractions asserted against the record.
  **AND THE INPUT PLAN INVERTS THE OBVIOUS ONE:** the refuted-run captures carry
  real grants and real snaps and are therefore CALIBRATION substrate, while the
  COUNTERFACTUAL substrate is the zero-grant set -- because `20260819T182652`,
  the capture that refuted `--client-endpoint`, yields **3.2 s and 259 u** of
  client track before its own first teleport contaminates everything after it,
  and because that zero-grant substrate is fast-running and click-free, which is
  the regime where every lead candidate is least harmful and where the shipped
  default survives by sending nothing at all. Every bracket is printed as
  `[match ON, match OFF]` and never as one arm, which replaces the drafted "skip
  the match test when chord p90 exceeds the radius" rule that fires on 4 of 4
  counterfactual and 7 of 11 calibration captures. **AND A MUTATION AUDIT PUT
  FOUR MORE CHECKS IN**, each pinning something that had been printed rather
  than asserted: §1(b)'s arrival tick now runs a SECOND leg of 150 u
  (520.833 ms, so trunc 520 against round 521) with both expectations
  HARD-CODED, because the old one recomputed `int(200000 / GS.COPY_SPEED)` --
  the same expression and the same constant it was checking, which left
  `COPY_RATE = 0.9` green; §2 pins the LEAD SPINE at 0 / 85.919968 / 766 u from
  what each policy GRANTS, because handing P2 the 766 u lead used to pass all 57
  checks while §9 printed "the match distance is 0 by IDENTITY" beside it; §3
  asserts that NO pattern's table sqrt lands exactly on either cut below its
  boundary (0 and 0, over the 2,048,001- and 2,560,001-pattern windows), which
  is the fact -- not a theorem -- that lets one `> cut` scan serve gate
  1's `> 300.0f` and the match test's strict `< 100.0`; and §5(d) pins the 2.0 s
  ACTIVE-TIME threshold against `movesync.FREE_SILENCE`, 5.27x apart on
  `20260820T182554`. §9's M1 bound moved from `2 * HISTORY_WINDOW` to
  `HISTORY_WINDOW`, since `lag_age` cannot legitimately exceed it and the factor
  of 2 was exactly the room its `lo` bound could be deleted in (4.55 s -> 7.42 s,
  still green). **§6b IS C3's HEADING ARM AND IT REPLACED A SKIP** on
  2026-08-21, the day `authsrv._heading_grant_ok` landed with REALFIX-P2's
  `--zero-lead`: `lead_policy` now imports and applies the SHIPPED rate limit
  instead of scoring P2 and P3 with none, and §6b drives BOTH arms of that
  predicate -- refused a microsecond under `GRANT_MIN_INTERVAL`, allowed at
  exactly it, allowed with nothing on record -- against hand-computed
  expectations, asserts the two arms' reason vocabularies are DISJOINT, and
  pins the policy end to end on the synthetic stream: **six moving headings
  0.25 s apart yield three grants** at `t = 0.00 / 0.50 / 1.00`, with the three
  refused ones producing no later grant, which is what "dropped, not held" means
  on the wire. **Its NEGATIVE CONTROL is a control now, and what stood there was
  not**: it compared the stream's six moving headings against those three grants,
  both of which the check immediately above already pinned, so it could not fail
  independently -- it added one to the floor and refuted nothing. The verdict
  hook is now rebound to always fire and the same stream must grant all six.
  **Beside it sits the check that keeps C3 honest on its own stated ground:
  the POLICY must RUN the shipped predicate, not merely import it.** Replacing
  `lead_policy`'s `heading_verdict(...)` call with an inline
  `fired = _since is None or _since >= 0.5` left this file green at 66 of 66 --
  the paraphrase-that-agrees-by-construction C3 exists to rule out, invisible --
  so the server's own `GRANT_MIN_INTERVAL` is perturbed (set and restored) and
  the policy's grant instants must follow it, from `[0.0, 0.5, 1.0]` to
  `[0.0, 1.0]`. A hard-coded 0.5 cannot. **And `replay_verdicts`'s heading-row
  filter is DRIVEN** against a hand-built capture carrying one `arm="zero-lead"`
  row, one bare `heading-rate` row and one ordinary click row as the positive
  control; both skip paths are exercised separately because the `arm` field is
  newer than the reasons and a filter keyed on either alone would miss the other.
  Deleting all three of those lines used to change nothing, since no capture in
  any vault has such a row. **It is deliberately NOT a message-level
  replay**: no capture in any vault holds a heading-arm `grant_verdict` row, the
  flag having never been run, and the banner says so -- **the first REALFIX-L1
  capture upgrades §6b onto the same footing as §6's 195137/195315 gate**, and
  `replay_verdicts` skips heading rows so that capture cannot silently
  redden the click arm when it arrives. §2's lead spine was RE-PINNED in the same
  commit, **6 grants per policy -> 3**, and its pairing fixed with it: the old
  form zipped grants against reports positionally, which is right only while
  every report grants, so keying on the report's own `t` is right under any rate
  limit. **The claim that the old form stayed silently green at 72.0 u is
  WITHDRAWN** -- measured both ways, the positional zip yields
  `[0.0, 72.0, 144.0]` for P2 against a required `[0.0]`, so it goes RED. The fix
  is right; the near-miss it was said to have caught never happened, and an
  invented blind spot is worth less than none. **§10 IS REALFIX-F1b's FIELD-4
  PRE-SCREEN, A DIFFERENT INSTRUMENT FROM EVERYTHING ABOVE IT** and the guard on
  `grantsim --planecarry`. Where §1-§9 score whether a policy would have
  *snapped*, this scores how many grants would have carried a field 4 that
  disagreed with the plane word the SYNC copy was holding — REALFIX-F1's own
  pre-registered falsifier, **the one it failed** — replaying three policies
  (shipped `--zero-lead`, F1 `--plane-carry`, F1b `--arrival-carry`) over the
  two REALFIX-L3 arms. **THE HEADLINE IT PRODUCES IS A NEGATIVE AND §10 PINS IT
  AS ONE: F1b does NOT reach 0, it reaches 3 of 69** on the F1 capture against
  F1's 6 of 93, and all three survivors land **8, 24 and 35 ms** after a
  modelled arrival the client had not yet acted on — a sub-frame race on
  `arrival <= now`, not a logic error, and a ~40 ms guard band that would close
  them is **REFUSED as a fitted parameter** with the refusal itself asserted in
  the printed report. **THE CALIBRATION GATE IS WHAT MAKES THE TABLE MEAN
  ANYTHING**: replaying each capture's *own* arm must reproduce its wire field 4
  on all 88 and all 93 grants and score the pin, which for the F1 arm is a real
  exercise of the policy since its slot advances only on a SEND and that
  capture's rate-limit refusals have to leave it alone. That gate also
  **corrected the published counts**: FINDINGS records 8 of 88 and 5 of 93,
  measured by pairing each grant with the *nearest* movetap sample — which can
  be one taken **after** the grant, and a sample after the grant reads the plane
  word the grant just wrote, scoring a genuine rewrite as a match. Pairing with
  the last sample strictly *before* gives **10 and 6**, and the 10 is
  corroborated by FINDINGS's own L3 table, which already reports "plane-word
  changes 10" beside the 8; §10 asserts **both** numbers so the correction is
  visible rather than silently applied. **THE ARRIVAL MODEL IS THE FALSIFIABLE
  HALF**: the SYNC copy's plane word has two writers — field 4 at the grant and
  field 3 again at **arrival** — and in the F1 capture 17 of the 24 changes are
  not at a grant and **all 17 land on a modelled arrival**, |dt| median 0.070 s
  max 0.135 s at a 9.5 Hz tap, with **zero free parameters** (the formula is the
  client's bake, the speed the 288.0 the client itself holds in 4,115 of 4,115
  samples). Its **control is a null that is asserted as unfalsifiable**: the P2
  capture makes **zero** client-authored writes, because under `--zero-lead`
  field 4 already equals the client's plane so the client never has to correct
  us — §10 requires `n == 0` there rather than letting a 0-of-0 read as a pass.
  The counterfactual is **observation-anchored and refuses contaminated
  grants**: field 4 is compared against the word movetap actually read, and once
  a counterfactual policy would have sent a different field 4 every later
  observation is a reading of the wrong history until a client write re-anchors
  it, so those grants are skipped and the denominator is printed beside every
  count (3 of 69 and 3 of 3 are not the same claim). **The closed simulation is
  kept, labelled and checked as a TAUTOLOGY**: it returns 0 for F1b because it
  derives the plane word from the same arrival model F1b's policy reads, and it
  **under-counts F1's own residual (3 against the wire's 6)** — §10 asserts both
  facts and asserts the printer says "BY CONSTRUCTION" and "TAUTOLOGY" out loud,
  because a model agreeing with itself printed as a headline is the failure this
  whole file was built against. Two of §10's checks are fixture-free — the three
  policies driven against a hand-built grant stream, separating on exactly the
  two-interval lag (`F1 [0,0,18]` vs `F1b [0,0,0]` with grant 2 still in flight)
  — so the floors move by **different** amounts, which is the case the two-floor
  split exists for. **§10 ALSO PUBLISHES THE SCREEN AS A CONSTANT AND PINS EVERY
  CELL OF IT.** `FIELD4_SCREEN` is the 3-policy × 2-capture table the server's
  `--arrival-carry` banner transcribes, and §10 checks all six cells —
  denominators included, because 3 of 69 and 3 of 3 are not the same claim —
  against the live computation, plus fixture-free that its diagonal *is*
  `FIELD4_MEASURED` and its F1b cell *is* `FIELD4_F1B_EXPECTED`. That is the
  half that gives `test_position_trust.py` §16's banner tie its meaning; without
  it the two files would agree about a number neither had measured. **And
  `FIELD4_PAIR_GAP` was split in two**: it was simultaneously the grant↔tap
  pairing tolerance and the grant-attribution radius, so neither could move
  without silently moving the other, and only the attribution role
  (`FIELD4_ATTRIB_GAP` now) was exercised — every grant's last-strictly-before
  sample lands within **0.122 s**, so all 88 and all 93 pair identically at
  0.25 s and at 5.0 s and a 20× widening moved neither the headline nor the
  pin. The pairing role is now bracketed from both sides by each capture's own
  cadence (the worst observed lead must fit inside the window; the window must
  not span three tap intervals), so it is a check the data can refute rather
  than a constant nothing reads. Floors **30** bare (§1's ten
  structural asserts, §2's nine refusals, §6b's seven predicate checks and
  §10's four fixture-free checks build their own fixtures and read neither
  vault nor client), RAISED to **86** once the fixture probes
  answer, because excess over a floor is not an error and a bare floor protected
  none of the checks only a full machine runs -- deleting C2(a)'s three
  structural zeros on a vaulted machine used to print ALL CHECKS PASSED and now
  names the shortfall. Both figures are re-measured from green runs of their own
  configuration, never 19+5 in anybody's head. §3-§9 declare seven
  `LEDGER.skip`s without the fixtures and there is no longer an always-on
  eighth. Reads only; sends nothing, writes nothing, and **does** import
  `authsrv.py` -- deliberately, see §6. No client. ~6 s),
  `toolkit/clientscan/test_probedoc.py` (THE PROCEDURE DOCUMENT QUOTES THE
  INSTRUMENT, and this is what makes that true.
  `studies/movement/PROBE-GATEFIRE.md` §6 tells an operator what `movetap` and
  `movesync` print during a live run, so a real run can be matched against it.
  **Those blocks were written before the instrument existed** and had drifted
  five ways at once by 2026-08-20: an `ALIASING: phi 0.011 ... white 0.409,
  A = 0.026.` line no code has ever printed, naming a `white` field no code has
  ever had; a 2-line fence header where the printer emits **3**; an
  `unread:*  0  0.0%` row that `fence_verdict` **cannot** emit, because it
  iterates `sorted(reach.items())` and a label with no occurrences is not in the
  dict -- structurally unprintable, not merely absent; an EPISODES section wrong
  in nearly every particular (no poll-rate line, no `effective n = ... QUOTE THE
  EPISODES.` line, ONE Nyquist threshold where the code names two -- DETECT and
  CHARACTERISE -- and no `a LOWER BOUND -- censored` marker); and a whole
  APPENDER WITNESS section attributed to `movetap`, which has no such printer
  (`grep -c appender_witness toolkit/clientscan/movetap.py` = **0**; it is
  `movesync.print_fence`'s). **Nothing caught any of it for as long as the
  document existed.** One block carried a RECONSTRUCTION label and the label was
  read as a licence rather than a debt -- §12 item 10 filed two of the five as
  accepted residue and undercounted the rest. A label on a shape does not check
  the shape; a rule nothing checks is a wish. So every one of §6's **15**
  untagged fenced blocks is now regenerated from the real printers and asserted
  against the document **byte for byte**. THE FIXTURES LIVE IN EXACTLY ONE PLACE
  -- `toolkit/clientscan/probedoc_fixtures.py`, 25 registered fixtures --
  imported both by this test and by whoever regenerates §6
  (`python toolkit/clientscan/probedoc_fixtures.py --write <dir>`), so the two
  cannot diverge; that single-source rule is the whole guarantee and splitting it
  voids the test. §1 pins the BLOCK COUNT before comparing anything, because a
  block quietly deleted would otherwise just stop being checked. §2 checks §6's
  own sha256 pin of `movetap.py` and `movesync.py` against the files on disk --
  the document says a moved hash voids every block below it, which is a claim
  about the source and therefore checkable, and it is the tripwire for drift in
  output §6 does NOT quote. §3 pins six printer SIGNATURES by name, including
  `gate1_verdict(g1, g1why, early_a, point_bad, n)` where `early_a`/`point_bad`
  are TALLY DICTS -- a caller passing ints raises `AttributeError` at
  `.get(True, 0)`. §4 asks the SYNTAX TREE (not a grep, which trips on the word
  "Whitespace" in a comment) whether any printable string literal in either
  module carries a `white` field, and whether `movetap` has an appender witness
  at all. §5 is TWO WITNESSES on each block's provenance tier: the document's own
  prose against the fixture registry. They must agree, so relabelling a block
  RECONSTRUCTION while a fixture still exists for it is a CONTRADICTION and goes
  red -- relabelling is not a way out. §6 is ONE loop over all fifteen with a
  tally asserting each produced exactly one outcome; a doc-marked or
  registry-marked RECONSTRUCTION is a DECLARED SKIP, never a silent pass, and the
  two OBSERVED blocks are re-run through `movesync`'s real CLI over the vault
  captures they name (`movetap-20260819T145939` x `authsrv-20260819T145717-c1`,
  and `--wire-only` over the second) or skipped where the vault is absent. §7
  renders every fixture TWICE and requires the two identical, including the 12
  not quoted in §6, because a fixture that moves between runs is noise and noise
  is how a bar gets lowered -- and a rotted unquoted fixture is worse than none.
  **Four sabotages were BUILT AND RUN on scratch copies and all four behave:**
  (a) one character inside Block 1 (`402` -> `403`) reddens exactly ONE check,
  naming the block, its document line range and the first differing line with
  both sides printed; (b) `WOULD` -> `MIGHT` in `fence_verdict`'s header on a
  scratch `movetap.py` reddens **8** -- the sha256 pin plus all 7 blocks that
  printer feeds; (c) Block 3 relabelled RECONSTRUCTION in the document alone
  reddens §5 and turns its content check into a printed `[SKIP]` carried into the
  verdict's "not measured this run"; (d) BOTH witnesses relabelled is green at 73
  with 1 declared skip, which is the shape a future block with no output yet
  takes. **(d) earned its keep by finding a real hole in the first draft of this
  file**: a `continue` dropped a registry-side RECONSTRUCTION with no check AND
  no skip -- a block that quietly stopped being covered, this document's original
  sin reproduced inside its own guard. §6's tally check is the fix — **and for
  eight days it was not, because the fix was written where the bug is invisible.
  REPAIRED 2026-08-29.** `handled += 1` sat as the FIRST statement of the loop
  body, above both `continue`s, so `handled == n` counted ITERATIONS: it printed
  `15 of 15 accounted for` and could not go red, which is a check-shaped no-op
  guarding the one hole this file exists to remember. It now counts the LEDGER's
  own movement — `(LEDGER.ran - ran0) + (len(LEDGER.skips) - skips0)` — so a block
  that falls through emits neither a check nor a skip and the sum comes up SHORT,
  wherever a future `continue` is put. Proved both ways by injecting the original
  sin (a bare `continue` on block 0): **14 of 15, red**, where the old counter
  said 15 of 15 and passed. WHAT IT DOES
  NOT COVER, named rather than implied: only §6's fenced blocks. §3's pre-flight
  greps (`gate_reach` = 31, `shut:apply` = 0), §5's build lines, §7's failure
  table and §10's addresses are prose and are NOT pinned. And the FIXTURE numbers
  are not measurements of the client -- real code over hand-laid input, so what
  is pinned is the SHAPE the code prints; §6, §11 and §12 say so per block and
  this test does not upgrade them. Floor **72**, the bare-machine subset, against
  a green **74** with both captures present. No client, no server. ~1 s),
  `toolkit/authsrv/test_handshake.py` (**the whole encrypted channel, end to end,
  and the only test in the suite that launches the server as a subprocess and
  speaks real protocol at it.** Sections: the vault-free key-binding regression
  guard (the key must bind to the ANNOUNCED build on BOTH channels); the exe's
  build matching the key file the server will load; the Diffie-Hellman exchange
  and the ARC4 key both sides derive; the two computer messages sent as ONE
  write containing TWO messages and then split across writes, because the real
  client does both; and the login burst, whose ORDER is the assertion --- every
  `CHARACTER_INFO` before `REQUEST_RESPONSE`, and `REQUEST_RESPONSE` last,
  because it is the only message that advances the client's login state machine.
  The negative control is an UNPATCHED client keying against ArenaNet's
  compiled-in B: its ARC4 key must NOT match ours, and it declares a skip when
  the vault holds no stock build with different parameters.
  **The 2026-08-29 lesson is about the test's own plumbing and it is worth more
  than the protocol coverage.** For four days this file reported
  `[FAIL] server sent a login burst  0 bytes` and, in the server's log,
  `ConnectionAbortedError: [WinError 10053]` --- which names a socket and reads
  as a protocol or crypto fault, and was NEITHER. The server's stdout was a
  `subprocess.PIPE` the parent read only at the END, in `drain_server`. A
  child's stdout pipe on this machine holds **4,096 bytes** (measured; CPython
  calls `CreatePipe` with `nSize=0`) and authsrv prints **3,822 bytes** of
  pre-registration banner BEFORE it accepts a connection --- 274 bytes of
  headroom, about four log lines, for the whole session. The server filled the
  pipe and BLOCKED IN `print()` mid-burst; the client, which was fine and
  reading, timed out after 10 s and closed; `drain_server` then read, the server
  woke into a socket that had gone, and its next send raised 10053. Nothing
  about it was specific to a build or a key --- it arrived when the BANNER grew
  past 4 KB, which is why it looked like the unpinned client build and was not.
  `start_log_reader` now pumps that pipe on a thread from the moment of spawn.
  **What makes that a fix and not a hope is the guard, and the guard's FIRST
  version was a check-shaped no-op**: it asserted the captured log was bigger
  than the pipe, which passes under the broken arrangement too --- a read at the
  end still returns every byte, because the child has exited and the pipe drains
  in one go. Size cannot tell a concurrent reader from a late one. WHEN can, so
  the guard reads how much the pump had already consumed at the moment the
  session ended: **4,305 B with the fix, exactly 0 B without it**, both arms
  measured 2026-08-29. Its capacity number is PROBED on the running machine
  rather than pinned, so the check compares two measurements rather than a
  literal, and it declares a skip --- naming itself VACUOUS, not passing ---
  when the log fits the pipe and no stall was possible. The same audit run over
  the tree found ONE other parent reading a child's pipe only at the end ---
  `toolkit/portal/test_webgate.py`, whose child writes **1,644 B**, 40% of
  capacity --- so it has real headroom and was left alone; the number is here
  so the next person does not have to rediscover the mechanism to check it.
  Floor **22**, the mandatory core; the pipe guard and the negative control are conditional and
  each raises the floor from inside its own branch, so a green run here prints
  **24**. Needs the vault and a free port 6112; ~9 s),
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
  fixture. Section 5 (2026-08-17, unitsetup Q9): the PARTY co-loads with every
  area, so its ids are reserved against area rows -- player 1, henchman
  30/definition 9, hero bodies 200..206/definitions 10..16 -- refused at load
  rather than at spawn, with the test enemy's ids as the deliberate
  NON-example (an area replaces it, so reserving agent 10 would refuse a
  collision that cannot happen). 51 checks, ~2 s),
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
  vault -- a segmentation defect is not a property of any one capture. §9
  (2026-08-17) pins the REPACKETIZED RETRANSMIT: exact-seq dedupe catches only an
  identical resend, and TCP may retransmit the same stream bytes split into
  smaller segments each carrying its own new seq, so every fragment survives
  `seen` and its bytes are counted twice. Found on live capture 20260817T183756
  connection …58389, which `load_tape` REFUSED with a 216-byte discrepancy while
  the seq span was exactly contiguous and `livesession`'s own reassembly agreed --
  a good channel rejected by a bad sum. `_drop_covered` now trims by covered byte
  RANGE; the section builds the defect synthetically and its SABOTAGE removes the
  trim to prove the refusal returns. Wraparound of the 32-bit seq is named as NOT
  handled rather than assumed away. 30 checks),
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
  `toolkit/authsrv/test_tickclock.py` (**the `0x001E` tick clock vs the wire clock over
  the WHOLE live corpus** — `test_smsgnames.py` §1 proved the payload IS elapsed
  milliseconds on the two 2026-08-07/10 captures its corpus deliberately pins; every
  timed claim since (the respawn pins, the burrow windows) rides captures that check
  never covered, so this one runs `behaviourrun.corpus_tick_sweep()` over all 54
  measurable live connections (5 short town hops counted, never dropped — as a SHARE
  since 2026-08-27: that was `short <= 6` against 5, an absolute cap over a corpus whose
  whole purpose is to grow, so the sixth town hop would have reddened a check whose own
  sentence reads *"stays small"*. Small is a proportion. Caught by doubling the live
  corpus with identical content, which took it 5 → 10 and reddened the old form having
  changed nothing, while the share held flat at 8.5% across the same doubling — which is
  what says it measures the sweep and not the vault. Cap 15%, a little under 2×, and a
  planted run where the sweep cannot measure 20% of connections reddens it). What it pins,
  from the 2026-08-23 sweep: the residual is a bounded transport-jitter WALK, not a
  clock skew — 52/54 walks end within 50 ms (most within 20), the 1,076 s connection
  closes at −4.6 ms (~4 ppm, the rate witness that rules out skew), and exactly TWO
  connections carry non-cancelling steps, both `20260817T183756` (+219.1 / −109.5 ms,
  a town-cadence 2 Hz tick connection among them), pinned by IDENTITY and exact value
  so a third step or a moved decode goes red. The breakage guard (|final| ≤ 500 ms and
  ≤ 1% of span) is deliberately looser than the jitter: real damage — a lost chunk, a
  misordered decode, a wrong clock scale — blows both bounds; honest jitter reaches
  neither. §5 is the part that feeds other studies: the per-connection ENVELOPE
  (max |residual|) is the wire-timestamp error bar a timed claim inherits, and the
  claim-bearing connections are pinned — the 120.499 s revive and 30 s respawn ride
  ≤ 100 ms envelopes (claims stand at ±0.08 s), while the 10.044 s player revive rides
  the +219 ms step (bar ±0.22 s, now quoted as ~10.0 s in studies/isle §10). Needs
  `vault/captures/live/`, skips whole if absent; floor 14),
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
  `toolkit/authsrv/test_charstore.py` (the §6 persistence layer against a scratch
  vault, no server started: round-trips, the client's settings blob served back
  verbatim, and ensure-never-overwrites — the disease persistence exists to cure is
  a restart quietly resetting a character. Its real checks are the REFUSALS: the two
  inputs measured to kill a real client on 2026-08-18 are refused at LOAD with the
  crash cited — an at-cap display string (string16(8) admits 7 units; at-cap is an
  instant Code=007) and a title referencing an unseeded rank (silent on receive,
  `Array.h(587)` at render) — and a corrupt or wrong-version store raises instead of
  silently becoming the default character. Its accrual half drives authsrv.accrue_kill_rewards with a fake send: xp lands on disk, the Balthazar current is CAPPED at the stored max while total is not, and with persistence off the kill template is a strict no-op. Floor 25, set from the green run; its faction half proves the DEFAULT world awards none -- the gate is the served map's content row),
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
  non-hostile definition may carry a health reading. Two sabotages run, both fail
  (the naive join, and `_f32` reinterpreting a dword's bits). Also:
  six definitions carry an EncString word in the UTF-16 surrogate range and were
  **unsendable by this server until the `string16` fix**. Since 2026-08-16 (Isle
  rung 5) the pins select the three captures BY NAME and the test proves a
  synthetic fourth keyed capture cannot move them — built into the vault and
  removed in a finally — plus the mode plumbing: base+reforged captures refuse
  to pool, a `--mode` contradicting a manifest is refused, and a recorded mode
  is used with no flag at all. **§7 (2026-08-22) retired a refusal that was
  wrong**: `read()` used to raise on a definition's second create-field-9 speed
  ("field 9 is single-valued"), which held only for the three keyed captures and
  blocked the full 15-capture pool — so every downstream unitassembly/unitmodels
  figure was a 3-capture number. Field 9 is the agent's speed AT THE CREATE TICK,
  so a snared create reports a reduced value: 9 of 2,931 creates over 2 of 189
  definitions, every one a snare fraction of the definition's own base (159: 288
  and 144; 114: 288 and 230.4), none above it. `move_speed` is now the base (max)
  and `move_speed_reduced` the snare states; §7 pools ALL live captures, proves
  `read()` no longer refuses, resolves **262 definitions vs the subset's 54**, and
  pins 159/114 by name plus the base-is-the-max rule. Floor 32→40),
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
  `toolkit/authsrv/test_damagepass.py` (the rung-7 damage-pass consumer —
  `studies/isle/PLAN.md` §6's exit criterion made runnable BEFORE the live session,
  because §7's named risk is measurements no line ever consumes. Three layers: exact
  math (H recovery must return the H the fractions were CONSTRUCTED from, with the
  MoD's predicted 590 in the family, and a three-value mixed-grid control proving the
  fit cannot be forced; the divisor fit recovers D=40 through all three estimators
  from ratios manufactured at D=40, reports spread 6.4 on a planted 10% distortion,
  reports None — not a complex number — when attenuation is absent, and REFUSES a
  missing AR=60 base rather than inventing §3.1's circularity); the B6 scoping rule
  (kind is part of the key; an NPC target keys on its STATION because the Suits die
  and respawn under fresh agent ids, a player keys per body-instance because a moving
  body at station granularity is many one-event groups); and retail pins BY NAME —
  map 146's fight (37 p16 + 3 p17), the rung-6 detour's map-310 arena (470 p16 +
  83 p17, ZERO unjoined, 105 projectiles — the largest damage corpus in the vault,
  recorded before this module existed), a player-class target's fraction grid
  recovering the 480 family (level-20 base health, a game-shaped number out of raw
  bytes), and the level-up `0x5D`'s cleartext args [13, 51, 1, 17] (B8's pin — the
  MoD announcement path). The p17 variance law is deliberately NOT asserted on arena
  data: bots cast skills, and the test instead PINS the confound — 10 of 11 arena
  p17 groups at n≥2 show nonzero variance, which is §3.1's attack-skill packet
  measured, and the reason rung 7 is auto-attack only. AR labels bind exclusively
  from the sealed plan's own step text (`AR=NN` / `RANK=NN` inside a mark window);
  one group under two labels refuses, events under no window carry None rather than
  a guess. The plan STEP joins the scoping key whenever mark windows exist — the
  rank-sweep extension re-engages ONE Suit at five ranks, and without the block
  dimension those blocks pool into a mean about nothing; `RANK=`-tagged blocks feed
  the rank curve and are excluded from the divisor fit by construction. **§7 pins the
  timebase join, and it pins a real silent bug**: `tape.load_tape` returns
  CONNECTION-LOCAL times (t=0 at that connection's first s2c segment) while plan marks
  are on the capture's GLOBAL wire clock, so reading events without adding `info["t0"]`
  shifts every label into a NEIGHBOURING step — mislabelled, not unlabelled, and nothing
  errors. On the rung-7 capture the 67.9 s offset put the Master of Damage's 42-swing
  block under the *walk* step and split the AR=100 block across two labels. The pins are
  refutable by construction: the two pure-walking steps must hold ZERO damage events,
  step 9 must hold exactly the 42-swing slot-144 block, and the bench must carry exactly
  the three pre-registered armour labels. **§7b is the attribute channel gate 1 asked
  for and no capture had ever carried** — a REAL rank reassignment: `0x0037
  [agent, unspent, 200]` and `0x003A [agent, ids | base | effective]` at instance load,
  `0x003B [agent, attr, base, effective]` per change and `0x0038 [agent, unspent]`
  mid-instance. It pins that the budget is 200, that the session's first unspent
  reading is 5 (matching the operator's own screenshot before any arithmetic), that
  `0x003A`'s two rank columns differ on Swordsmanship alone — the **+1 bonus visible on
  the wire** — and that all 14 changes name attribute 20 with effective = base + 1. The
  point costs then close two independent ways: three equations over four instance-load
  readings give cum(8) = 37, cum(10) = 61, **cum(12) = 97** with no cost table assumed,
  and the sweep connection's own debits (41→25→5) reproduce the same 36 while splitting
  it into rank 11 = 16 points and rank 12 = 20. Needs `vault/captures/live/`; without it
  the corpus sections cannot run and the floor of 64 takes it red),
  `toolkit/authsrv/test_bufflog.py` (the rung-8 effects consumer — `0x0042` apply /
  `0x0044` remove read as EPISODES, built before its live session the way rung 7's
  analyzer was. **Its retail pins carry a headline that retires the rung-8 design's
  central worry**: `studies/isle/PLAN.md` §3.3 says `0x0042` has ZERO ArenaNet
  witnesses, so "conditions ride some other channel" was the expected outcome — the
  corpus in fact holds **97 retail applies and 88 removals**, six of them known
  CONDITION skill ids, arriving in the rung-6 arena detour and the east run's Pin Down.
  The removal lands at **apply + duration** (median 1.3 ms on the arena connection), so
  an episode closes EXPIRED, STRIPPED (early — all four in the corpus are one stance
  cut by 3.6–8.7 s) or OPEN (still live at the last byte, never scored as expired). The
  synthetic half attacks the pairing where it can silently lie: **buff ids are reused
  within a session**, so a global id→apply map pairs an apply with a *later* episode's
  removal and reports a wild residual while looking fine; two targets holding the same
  id at the same moment must not cross-pair either. **A CURE is pinned from ArenaNet's
  own wire, the first in this repo**: the Isle's Crippled episode is stripped 11.2 s
  early and skill 364's apply carries the *identical* timestamp as that removal — so a
  cure closes a condition through the same `0x0044` an expiry uses and only the residual
  separates them. Also pinned: the attribution REFUSAL (`0x0042` has no source-agent
  field, so an episode outside every mark window stays `step = None` and is never
  assigned to the nearest step), and the float-in-a-dword trap (the duration is typed
  `dword` while the client does `fld`, so the broken reading is reproduced inline and
  required to differ). Needs `vault/captures/live/`; floor 36),
  `toolkit/authsrv/test_respawn.py` (**the rung-9 respawn consumer, built before its
  run per the arc's own consumer-before-run rule** — `respawn.py` keys death → revive
  intervals on (definition slot, spawn position) with a preceding-death bit, the key
  `studies/isle/PLAN.md` §3.4's skeptic demanded. Sections 1–14 fabricate streams that
  commit each named trap and demand the analyser refuse it **while
  `respawn.naive_intervals` still falls for it** (the `npcdefs.Intervals.last` pattern
  — a sabotage that stops disagreeing has drifted): the recycled agent id (agent 38's
  54.9 s "respawn" by a creature that never respawned), visibility churn, and the
  corpse re-create — `WORLD_CREATE_AGENT` kind **8** is a DEAD NPC re-entering view
  with health fraction 0.0, so a death→create join reads a corpse as a respawn; the
  analyser reads it as a STILL-DEAD bound instead. §15 pins the real corpus
  per-connection (per-connection so the pins survive corpus growth): agent 38 stays
  OPEN while naive claims 54.867 s; slot 161's Zaishen revives **in place** at
  **120.499 s** (GWW's "two minutes", measured) while naive joins the corpse and is
  9 s wrong *even though the respawn is real*; the Isle sparring squad's 19 deaths all
  corroborated by `0x00F1`'s dead bit; **nine practice-target revives in one
  connection at 30.0 ± 0.011 s** (GWW's "30 seconds", measured); and the two-track
  `0x0026` life-state reading — NPC dead/alive = 8/9, PLAYER dead/alive = **4/5**, a
  pair the old 204-sample histogram in `authsrv.py` predated — holds with zero
  value/tag mismatches and no fifth value corpus-wide. Also pinned: mixed-origin
  pooling refuses (`refuse_mixed`), a corpse-first chain revives with an interval that
  REFUSES to exist, and `--radius` merges print every merge. Needs
  `vault/captures/live/` for §15, skips it declared if absent; floor 46),
  `toolkit/authsrv/test_effects.py` (**the effect channel's WRITER**, where
  `effects.py` meets the reader above. R4b's spine: `0x0042` opens an episode on an
  agent and `0x0044` closes it, and until 2026-08-20 this server modelled none of it
  — `authsrv.py` knew `EFFECT_DEAD` and `EFFECT_TRANSITION` and nothing else, so every
  skill whose scale was not damage resolved to nothing. **§2 is the check the module
  rests on and it has NO FREE PARAMETER**: for every apply in the live corpus, predict
  the f32 duration on the wire from the applying skill's own `duration0`/`duration15`
  endpoints in the CLIENT'S table at rank = field3, using the client's own two-point
  scaler — **96 of 96 non-condition applies land exactly, 0 miss**. The endpoints are
  ArenaNet's, the formula was measured at `0x005A8920` for the DAMAGE scale, and
  field3 and the duration are retail's own bytes, so our decoder cannot force it true.
  **That settles `bufflog.field3_report`'s registered open question** — (a) field3 is
  the applying skill's attribute RANK, (b) it is a duration-shaped field — which its
  docstring said was "one session away". It was ZERO sessions away and the
  discriminator was already in the vault: skill 160 carries field3 = 15 against a
  duration of 13.0, and skill 364 appears at two field3 values (10, 13) producing two
  durations (10.0, 12.0), both predicted. Reading (a) CONFIRMED, (b) REFUTED.
  Conditions are counted SEPARATELY and a check requires that some of them genuinely
  break the rule, so "excluded" cannot quietly become "they agree too" — 480 has
  endpoints 3/3 and appears on the wire at 9.0, because a condition's duration comes
  from the skill that inflicted it. (The corpus now holds **102** applies; the 97 in
  the entry above was true when it was written.) **§1 walks the duration rule branch by
  branch, and every permitted branch names a retail witness while every refused branch
  names its zero**: bit SET → interpolate (160, 364, 348, 814); bit CLEAR with EQUAL
  endpoints → the flat value (**984 and 998, which retail sent at duration 30.0 with
  the bit CLEAR — so the bit means the duration SCALES, and a server honouring it the
  strict way cannot reproduce two of retail's own applies**); a SENTINEL → refuse
  (0x20000 ×22, 0x30000 ×7, 999999 ×1, and 24 of the 30 are enchantments, which is
  where "maintained until removed" belongs — Vital Blessing 289 is one and it is on
  our own enemy's bar, so this refusal fires every session); DIFFERING endpoints with
  the bit clear → refuse (49 skills, zero witnesses). **§1c is what licensed adding Glyph without waiting for a run**, and it is
  refutable by construction: across the **478** corpus skills in the five effect
  types, **not one** resolves to "no duration" — 74 of 76 stances, 9 of 10
  glyphs, 13 of 14 preparations, 142 of 151 hexes and 194 of 227 enchantments
  resolve and the rest refuse on a sentinel. If "this type IS a timed effect"
  were the wrong mapping, the giveaway would be a type full of skills with
  nothing to time. The control is the other side of the partition: **488**
  corpus skills DO have 0/0 endpoints and **none** is an effect type.
  **§§4c–4d are the ONE-AT-A-TIME rule**, which is also the first answer this
  repo has to "how does an effect get REPLACED" — re-sending `0x0042` does
  nothing, measured under both id choices, so a replacement has to be a real
  `0x0044` then a `0x0042`. Three of the five types carry the rule and two say
  it in text the game shows a player: WIKI (GWW "Stance", quoting Isokeh in
  game) *"Only one Stance can be active at any time... using a new Stance will
  replace the previous one"*; (GWW "Preparation") *"Only one preparation can be
  active at a time"*; (GWW "Glyph") *"the new one replaces the old one"*. It is
  per TYPE and per AGENT, hexes and enchantments carry no such rule (the
  control), and the TABLE deliberately does not enforce it — the CALLER does,
  because the replacement is a wire operation and an episode dropped silently
  leaves its icon on the client's screen. §4d pins that the server sends REMOVE
  **then** APPLY, in that order, naming the old episode's buff id.
  **§3's negative is the point**:
  Desperation Blow carries a real 2-second duration and is an ATTACK, and nothing in
  the table says what those seconds are, so it opens nothing — the same refusal
  `SCALE_MEANS_DAMAGE` makes one layer up. A Shout opens nothing either, *even though
  the corpus's own witnesses include two of them*, because party-wide shouts break the
  premise that the target byte names the recipient. §3b pins the target byte with the
  type column as its witness (all 199 Attacks are 5, 75 of 76 Stances are 0) and pins
  that an UNRESOLVED code degrades to the caster's own choice rather than to a guess
  about the enum. §4 is the table — ids distinct among LIVE episodes and reused after
  close, which is every property the corpus actually pins; `due` oldest-first; a double
  close returning None rather than raising; a zero-length episode REFUSED. **§4b pins
  retail's allocator against a fix of ours that was made and reverted**: a client run
  showed one icon for four concurrent episodes of one skill, so the table was collapsed
  to one episode per (agent, skill) — and the corpus then refuted the collapse, holding
  **15 overlapping re-applications, every one under a NEW buff id** (120→121 at a 0.43 s
  gap), with the first still closing `expired` on its own duration and same-id repeats
  only ever occurring after a close. The section carries the client fact that started it
  too: a repeat `0x0042` for a live (agent, skill) is DISCARDED, measured under a new id
  and under the same one — the latter a **stated prediction that was refuted** — so how
  retail refreshes an effect is NOT FOUND, and the real defect is our placeholder AI
  re-casting a hex the target already has. **§5 runs our
  own emission back through `bufflog`, the reader written for retail's**, and requires
  `expired` with a zero residual — *with a control that closes the same episode early
  and must read `stripped`*, so the check discriminates rather than agreeing with
  whatever it is handed. It also pins the float-in-a-dword trap from the writer's side.
  §6 pins that death STRIPS (per-agent — the enemy's hex survives the player's death)
  and that `--no-effects` is a real control. Needs `vault/captures/live/` and the
  pinned client for §2, which is declared as a skip naming what a green run without it
  has actually checked. **§§4e-4g are DEGENERATION**, which is what makes a
  condition do anything and which closes `studies/isle` B4's one open clause.
  The pips are GWW's (*"each pip represents a loss of two health per second"*;
  Bleeding 3, Burning 7, Disease 4, Poison 4, capped at 10) and the other six
  conditions degenerate nothing -- a fact, not a gap, with Blind and Crippled as
  the control. Bleeding on a 100-health player is pinned at exactly `-0.06`/s on
  `0x00A2`, the NO-TARGET float twin (PLAN.md 3.3 had these properties on
  `0x009F`; the corpus put them here). An UNCHANGED rate must send nothing, a
  steady tick must send **nothing at all** -- B4's *"passive ticks are never
  streamed"*, so the server spends health silently and the client animates from
  the one rate -- and an EXPIRY must push the rate back to zero, which is the
  half a server forgets: the icon goes and the arrows stay. **§4f0 is the
  no-stack rule, and a run forced it**: with the enemy's Sever Artery on a 0 s
  recharge the player picked up FIVE Bleeding episodes, 3 pips then 6 then 9 then
  the cap at 10 -- twenty health a second. WIKI (GWW "Condition" Notes):
  *"Reapplied conditions will last the original time period, unless the reapplied
  duration is greater than the remaining amount of time."* So a shorter
  re-application is a no-op in the table AND on the wire, and a longer one
  extends as REMOVE-then-APPLY; floor 74),
  `toolkit/authsrv/test_mechanics.py` (**the episodes finally DO something** — the
  2026-08-22 layer over the substrate: Frenzy's attack speed and doubled damage,
  Reversal of Fortune's conversion, the glyph's discount live, the preparation
  bonus, the gated movement base. Its pins are numbers GWW itself publishes, so
  neither the rule nor the row can drift silently: **the +33% hammer must land on
  exactly 1.1725 s** — GWW's "Attack speed" table lists the exact values the game
  uses, the percent CUTS the attack duration (×0.67), and the check's own detail
  text carries how far the plausible /1.33 reading misses (0.14 s a swing — a
  formula this arc nearly shipped); **rank-12 RoF must convert GWW's own worked
  example exactly** (a 67 hit under Frenzy doubles to 134, cap 67: 67 reduced, 67
  healed, 67 lands), the heal goes out BEFORE the episode closes, and a second
  hit lands whole — one packet, one conversion. `skill_flat_constant` is the
  bit-clear-EQUAL rule (Rush's 25, Frenzy's 33, the glyph's charge count 2 from
  the client's own bonus slot) with both refusal directions checked; the retired
  at-cast cap-heal is pinned retired (`skill_heal(307)` is None while Healing
  Signet still heals); the glyph pipeline runs Flare to a floored-at-zero cost
  and spends exactly two charges into one real 0x0044; the preparation bonus
  gates on the weapon row's `fires_arrows` (no bow type-code enum has a witnessed
  value) and stays inert on the starter hammer; and the movement lever is pinned
  OFF by default, with ON declaring 360 once, deduplicating, and RESTORING 288
  when the stance ends. §9 drives `land_swing` end to end: control, doubled, and
  fully-converted swings, with MELEE_ATTACK_FINISHED still opening the batch and
  NO damage message after a full conversion. Offline, no vault; floor 39),
  `toolkit/authsrv/test_pools.py` (**what a skill COSTS** — R4b's other half, where
  `effects.py` models what a cast puts ON somebody and `pools.py` models what it
  takes. Until 2026-08-20 this server took nothing: two harness runs that day pressed
  eight skills including Flare (5 energy in retail) and the player's orb sat flat at
  25, because nothing here had ever sent a property 62. **§2 is the section that
  carries the module and it has NO FREE PARAMETER**, the same shape `test_effects`
  §2 established. Energy has no opcode of its own — it rides the generic property
  channel — and the whole model is one quantum: **`rate = f32(0.33) * pips / max`**,
  which reproduces **all five** of retail's distinct property-43 values BIT-EXACTLY
  while the nominal rule every source states, one third of a point of energy per
  second, reproduces **zero** of five. §1 is that discriminating negative, and it
  also pins that the constant is a `float` and not a `double`: `f32(0.33*p/m)` from
  the double gets 2 of 5, rounding 0.33 to f32 FIRST gets 5 of 5. **The check with no
  free parameter is the pips**: join each of the 52 property-43 events to that
  agent's own property-41 maximum (52 of 52 join, none orphaned) and solve — every
  one lands on an INTEGER, and on the integers GWW's armour table predicts (base 20
  energy / 2 pips; Ranger +1/+5, casters +2/+10). A wrong constant has no reason to
  produce integers at all. §2 also predicts all 45 property-62 spends from the
  client's own energy-cost column; crosses every activation in the corpus against
  them into a **2×2 with TWO EMPTY CELLS** — the observing player's own agent spends
  on 45 of 45 paid casts and 0 of 44 free ones, and **722 casts by other agents, 579
  of them paid, carry not one spend**, which is what makes "property 62 is the own
  agent's and nobody else's" a rule rather than a tendency; and confirms **property
  33 — an absolute "your energy is now N" — appears 0 times in 13,378 property
  messages** while the positive control finds 97 and 52 of its neighbours in the same
  scan, so the client INTEGRATES energy itself and a server that sends no deltas
  leaves the orb flat. §§3–4 are the two pools as state machines: the death penalty
  re-sends the SAME pips over the NEW denominator (0.0528 → 0.06, OBSERVED n=1),
  a zero-cost cast returns None rather than 0.0 so a `-0.0` cannot reach the wire,
  and adrenaline is WIKI throughout (25 units per weapon hit; 1 unit per 1% of max
  health lost, FLOORED, with zero damage granting nothing **and not counting as
  combat** — a control proves a real gain at the same instant DOES refresh the
  25-second clock). **Costs are RAW UNITS and not the number on the icon**: Battle
  Rage is 80 raw displayed as 4, and GWW's own Notes say it *"exactly requires 80
  units of adrenaline (3 strikes and 5 units)"* — four strikes would be wrong by a
  whole hit. **§§5–10 are the GLUE**, driving `authsrv.py` through a fake `send`.
  §5 does not test new code at all and is the one to read first: it asserts that
  `agents.PLAYER_FLOAT_43` — the 0.0396 shipped since it was copied out of
  gw-preservation with *"purpose unknown upstream too"* beside it — **IS**
  `wire_regen_rate(3, 25)` bit for bit, three pips over the 25-energy pool the same
  spawn burst already declares. The magic number was a measurement. §6 presses Flare
  and requires exactly one property 62 at f32(-0.2) on `0x00A2`; §6b requires an
  unaffordable press to produce **not one message** and no pending cast (the refusal
  SHAPE is RECONSTRUCTION — retail's answer is unobserved and the client may swallow
  it locally — but a half-refusal is wrong under every reading); §6c pins the free
  cast sending nothing; §6d proves `--no-energy` is a real control and that the
  default is ON. §7 charges Sever Artery with four landed swings **through
  `hit_enemy`**, spends it, and requires every other pool down exactly one strike —
  paid at USE, "whether or not the skill is interrupted or fails", the opposite of
  the energy spend. §8 is the death batch (property 43 → 0.0) and the resurrect batch
  (52 = 1.0 and 43 back to the rate) with a PREDICTION on record: the orb sticks at 0
  after a revive today, and must refill once these go out. §9 pins the glyph hook AND
  the row it is waiting on — skill 200 is the only content row labelled `Energy` and
  its amount is **refused**, because the client gives it 10→18 with the scale bit
  CLEAR and `resolve_duration` already sets the precedent that bit-clear DIFFERING
  endpoints have zero witnesses; the discount, the two charges and the closing
  `0x0044` are then exercised against a stubbed amount, with an ATTACK skill at the
  same cost as the control — and since 2026-08-22 the section also pins the
  queued-press split: the CHARGE burns at the press (so a third stacked press
  cannot be quoted a discount the glyph no longer has) while the queued press's
  DEBIT waits for its cast-begin, fired by rewinding the pending entries through
  `cast_tick`, and still pays the press-quoted discounted price. §10 is the enemy's gate, which rate-limits the
  heal-spam PLAN.md §8 item 4 names without touching the round robin, and requires
  **no property 62 for it** — 0 of 722. **§11 is the ADRENALINE FAMILY ON THE WIRE
  (2026-08-21)**, and the paragraph it replaced is the reason it is worth reading:
  this file used to assert *"NOTHING about the adrenaline goes on the wire"* because
  no upstream catalog names an opcode for it. Four do — `0x00CF` charge, `0x00D0`
  clear-all, `0x00D1` absolute set, `0x00D2` spend — and `test_adrenwire.py` carries
  the model while §11 carries the SENDER. All four encode through the real codec to
  the **client's own declared sizes** (10/6/16/12); a landed weapon hit puts out one
  `[player, 25]` in RAW UNITS because the client ADDS the message's number to each
  slot; **the enemy's pool moves and not one message names it** (self-scoped 9 of 9 —
  and the target is 100 health precisely so its own pool clears the 1% floor, because
  the first cut used a 5,000-health dummy and the silence was vacuous); a sub-1% gain
  sends nothing with an 11% control at the same call site that does; the spend lands
  **immediately before the property naming the skill**, 39 of 39 in the corpus —
  property 50 in all 39, the attack-skill flavour, which the press has picked for
  that family since 2026-08-22, so §11e pins the id too (family forced via a
  stubbed `_is_attack_skill`, bare machines having no rows) — and
  carries **no property 62** — which is ArenaNet's own
  `!(energyCost && skillData.adrenaline)` asserting at two independent sites that a
  skill cannot carry both costs, so that order never has to be decided. **§11f is the
  client's RECHARGE SKIP** (`cmp [esi+8],0 / jne` at `0x008219C0`) mirrored into the
  pool with its own control — the divergence it closes would be permanent, because
  209 is the only message that could correct it and retail sends it **0 of 724**.
  §11g puts the death clear **LAST** in the batch and says why the corpus cannot rule
  (the cell is EMPTY, not zero: no connection carrying adrenaline ever witnesses its
  own agent dying), so an unmeasured message goes after a measured sequence rather
  than inside it. §11h requires the timeout wipe to be an **isolated** `0x00D0` and
  nothing else, which is retail's own shape — 15 of 15, at 24.973–25.015 s. §11a also
  counts `AGENT_ADRENALINE_SET` in `authsrv.py`'s source text and requires exactly
  **one** occurrence — a declaration and no send site — and ties those constants to
  `schema/overrides.json`'s four names, which the derivation pass wrote off the
  client's own descriptors and the wiring pass wrote off the house naming rule with
  nothing forcing them together. Needs `vault/captures/live/`
  for §2, declared as a skip; needs the client-table content overlay for §§5–11, which
  is NOT skippable and should go red without it; floor 108 of a 125-check green run.
  **11j pins `--refusal-silent`, the A/B arm SKILLS-R2 rests on** — both directions,
  plus an explicit third check that the two arms actually DIFFER. An arm that
  silently stopped suppressing would make the next A/B compare two identical
  configurations and report a clean null, which is the most convincing way to be
  wrong (see `studies/skills` §37.5 for the session where exactly that shape of
  null nearly shipped from a different cause)
  (was 82 of 98 before §11)),
  `toolkit/authsrv/test_adrenwire.py` (**adrenaline IS on the wire, and this is the
  file that stops us forgetting again**. Until 2026-08-21 `pools.py`'s header read
  *"ADRENALINE IS NOT ON THE WIRE AT ALL, and that is a finding rather than a gap"* and
  `authsrv.py` repeated it — a floor (nobody had looked) read as a ceiling, the same
  error shape CLAUDE.md records for the provenance gate. **Four
  opcodes carry it**: 207 `{agent, units}` the CHARGE, 208 `{agent}` CLEAR ALL, 209
  `{agent, skill, copy, units}` an ABSOLUTE SET, 210 `{agent, skill, copy}` the SPEND.
  **The names are OURS** — NOT FOUND in maintained GWCA, OpenTyria, Headquarter, GWLP-R,
  Py4GW_Reforged and gw-preservation, all searched — so no §6.1 register row is owed and
  no upstream can corroborate them either; the client and the corpus are the only two
  witnesses and the file is built out of both. **§§1–3 are the mandatory core** and need
  neither: the four declared shapes out of `schema/messages.json`, a tripwire tying this
  file's own census constants to each other (631 + 32 = 663; 20+11+8 = 39, so HALF an
  edit goes red rather than passing two mutually inconsistent sections), and the one that
  is a real finding — **adrenaline costs are NOT all multiples of 25**. Seven distinct
  costs in ArenaNet's own column (80, 120, 130, 140, 160, 220, 240) are off the grid, so
  25 is the GAIN PER STRIKE and not the quantum of the bar, which is why
  `pools.AdrenalinePool` holds RAW UNITS; the control is that eight other costs *are*
  multiples, because an all-off-grid column is what a wrong offset also produces. **§§4–7
  are the corpus oracle**, `test_pools` §2's shape over the live captures: **at least**
  918 / 27 / **exactly 0** / 40 across 59 connections and 143,408 messages framed with
  zero errors (663 / 22 / 0 / 39 over 49 connections when this entry was first written,
  at 14 captures; 921 / 28 / 0 / 40 over 61 connections and 146,660 messages on
  2026-08-27). **THOSE ARE FLOORS SINCE 2026-08-27, AND THE FILE WENT RED ON MAIN TO
  EARN THEM.** They were equalities, so a corpus that grew reddened this file on evidence
  that CONFIRMS every claim it makes — 207 went 918→921, 208 went 27→28, the 25s went
  886→889, and not one reading moved. It was the *second* such re-pin (14→20 captures was
  the first), which is what says the shape was wrong rather than the numbers. A floor is
  also what the original comment actually asked for: *"A corpus that shrank is a vault
  that moved, and every count below would quietly get easier."* Shrinkage is the defect;
  growth is the campaign working. **What stayed exact is what is actually claimed**: 209
  is `== 0`, no 207 exceeds 25 units, the sub-25 tail is still the same multiset (stable
  across two corpus growths, which is itself the interesting fact), and §12's armed side
  carries the *whole* family — that last one now compared against **§4's measured census
  rather than a third frozen copy of it**, so the "two queries agreeing" it advertises is
  finally two queries and not both agreeing with a constant. A new check carries the
  durable form of the strike count: 25 is the *overwhelming* mode, >20× the tail, which a
  re-pin could never paper over. Six deliberate breaks all redden it, including a shrunk
  corpus and a nonzero 209.
  **COMPLETED LATER THE SAME DAY — that pass fixed the four checks that had ACTUALLY
  reddened and left nine more of the same class standing.** Found by a rig rather than by
  reading: the live corpus was DOUBLED with identical content (a shadow vault of
  junctions, 21 stamps → 42) and every test that reads it re-run, on the principle that a
  corpus which merely got bigger must not redden anything. Nine checks here did. Two were
  worse than stale — §6's `spend_copies` and §7's activation join compared a LIVE count
  against `CENSUS[…]`, *the very constant the morning's pass had redefined as a floor*,
  so the same number meant two things three hundred lines apart and was green only
  because nothing had been captured since; both now read `agg["census"][…]`, the
  measurement. The rest became relations the counts cannot stale: the two damage arms now
  score **the GRANT** (`armed` all granted, `dark` exactly none) with the counts as
  floors and the row count cross-checked against each arm's own counter, which is what
  their detail strings always said mattered — *"the two populations happen to be the same
  size, which is a coincidence and not a check"* — and which nothing had actually
  asserted, since no check read `units` at all; `fits` keeps **round-fits-ALL** exact and
  floors the population; `spend_skills` becomes a floor per skill; and the skipped-
  connection cap becomes the PREDICATE it always claimed (*every skip is a 6112 auth
  channel*), so a skip on a game channel — the one that would mean the observer had gone
  unidentifiable — is now named instead of tolerated. **Two exact corpus claims are
  deliberately LEFT exact and the constants block now says so**: the sub-25 tail multiset,
  and §13's `len(band) == 1` near miss, where a second row is the single observation that
  would settle round-vs-ceil. Reddening is the point there; investigate, do not widen.
  Eight deliberate breaks, eight red — one per repaired check. Under the doubled corpus
  the file now reddens on exactly those two deliberate claims and nothing else. The zero
  is the one to read — **209 is a fully wired handler retail never sends**, the same shape
  as energy property 33, with its three neighbours (724) as the positive control that
  makes a null mean something. §4b splits 207's amount into **886 at exactly 25 and a
  32-message tail below it**, and pins that **none exceeds 25 and none is 0** — the strike
  rule's own signature, since 25 is the largest single event the rule allows and the
  opcode is unsigned so it cannot express a loss. The tail was labelled **INFERRED, not
  measured** — GWW's *1 unit per 1% of maximum health lost* produces exactly this ragged
  shape — and **§12 now joins it**, one row at a time, to the damage that caused it. **§5 is the
  check that refuted a wrong reading** — an earlier draft claimed retail broadcasts 207
  for other agents' bars, on the strength of ids 7/11/13/25 across the corpus. Those are
  four SESSIONS: every connection carrying 207 names **exactly one** agent and it is that
  connection's own `SKILLBAR_UPDATE` (218) agent, 9 of 9 — **and the control is what makes
  it a finding**, because those same connections carry 9 to 24 distinct agents on the
  property channel, so "one agent" is a property of the opcode and not of a thin capture.
  §6 joins all 39 spends to the client's own cost column (382/384/385, all nonzero) with
  the control that gives it teeth: the same lookup over everything the corpus shows being
  CAST finds **753 casts of 50 ZERO-adrenaline skills**, none of which ever gets a 210.
  **§7 is the answer the sender needs** — the spend leads its own activation by **exactly
  one message**, 40 of 40, same batch (the FOLLOWER is property 50 for attack skills and
  48 for instants — a live capture of a shout broke the "always 50" half and left the
  half the sender uses intact); the energy channel orders
  itself the same way (property 62 then 60), so "debit before announce" is a rule of this
  protocol rather than a quirk. **§§8–11 read the pinned build-38797 image, stdlib only —
  no capstone, no pefile, so it keeps working on a bare machine.** §8 walks the dispatch
  chain as **arithmetic** rather than comparing addresses with themselves: four
  descriptors at a 12-byte stride whose type arrays declare 0xCF…0xD2 **in order** (which
  is what makes `0x00BC96B8` opcode 207's descriptor rather than an address we chose to
  call that), field counts that agree with `schema/messages.json` **4 of 4 from two
  independent derivations**, and each handler's rel32 resolved stub → thunk → worker.
  §9 pins the stores, including the identity **4 + 8 × 0x14 == 0xA4** that three separate
  immediates in the charge loop have to satisfy, and the one worth reading twice: the UI
  event loads a **FIXED 25.0f from .rdata**, not the message's amount — so a 3-unit gain
  and a 25-unit gain produce the same flash, which is why §4b's tail is invisible on
  screen and had to be found in the bytes. **§10 is the correction this build owes**: the
  icon draws from **+0x04**, not the +0x00 PLAN.md named, proved by two functions
  indexing the same stride at 4 and at 8 — a deferred-commit double buffer. It also pins
  **the map gate**, which changes probe design: the fill is drawn only in
  `MISSION_MAP_GAME` (== 1) and is actively TORN DOWN otherwise, so a perfectly correct
  207 sent to a client sitting in an outpost yields a **pixel-identical icon** and a null
  from an outpost run means nothing. §11 cites **four assert sites singly**, each as the
  evidence for one claim per CLAUDE.md's measurement boundary — `ChCliSkill:84`
  *"context->skillAdrenalineUpdateArray.Count()"* names the whole deferred chain, and
  `skillData.adrenaline` at **two independent files** promotes `skilltable.py`'s
  `adrenaline_units` decode from our name for the column to the client's own.
  **§12 is the sharpest refutable claim in the file, and it is a SERVER behaviour we do
  not implement.** Split the 58 usable connections on a variable that has nothing to do
  with adrenaline traffic — does the observer's own `SKILLBAR_UPDATE` ever name a skill
  with a non-zero adrenaline cost — and the whole family falls on one side: **918 / 27 /
  40 in the 36 ARMED connections and 0 / 0 / 0 across 44,982 messages in the 22 DARK
  ones.** The control is inside the negative population and is what makes the zero mean
  something: those dark connections carry **45 landed weapon hits and 13 completed melee
  attacks**, every one of which GWW's rule says earns 25 units, and retail sent none. It
  also re-fits the rounding rule on the armed rows alone — **round 32 of 32**, floor 15,
  ceil 17 — and it does NOT stop there, because a two-candidate test would have hidden
  the real result: fit the rule as a FAMILY, solving `units == f(pct·k)` for the k
  interval that fits all 32 rows, and **floor is EMPTY under every rescale** (which
  refutes GWW's "rounded down" *and* the pre-mitigation-damage repair of it in one
  line) while **round and ceil both survive and disagree at the low end** — a 1-point
  hit is 1 unit under ceil and no message at all under round. And it pins **the near
  miss**: exactly ONE damage event in twenty captures lands in the band where those two
  disagree, its observer's bar has no adrenal skill so there was nothing to charge, and
  its value is **0.999999978%** — which four decimal places render as "1.0000", exactly
  where the two rules agree. Three independent readers printed it rounded and all three
  read past it. It also runs the check
  with no free parameter: all eleven armed percentages are **k/480**, 480 is the smallest denominator that works, and the observer's int property
  42 reads 480 on a message none of that arithmetic touched. What it deliberately does
  NOT assert is WHICH variable gates: every dark connection is also a non-Warrior, so
  bar-based and profession-based rules fit all 58 identically and the sender implements
  neither. This section exists because running the damage → gain join WITHOUT the split
  reports a confident, clean and absurd boundary at 7.5% of maximum health.
  **§13 is why nobody saw §12 from the screen**, read as arithmetic on three addresses:
  the charge worker does `xor edi,edi` before its slot loop, `mov edi,1` only where a
  slot is written, and `test edi,edi` / `je` at `0x008219F8` — whose target is computed
  from the displacement and lands PAST the `push 0x10000058` — so a 207 that no slot
  accepted repaints nothing and arms no 25-second timer. Needs
  `vault/captures/live/` for §§4–7 and §12 and the pinned image for §§8–11 and §13, both
  declared as skips; the content overlay is NOT skippable and §3 goes red without it.
  **Floor 10 of a
  72-check green run** (55 before §§12–13), and the file says plainly what that floor
  cannot catch — on a
  machine with both fixtures a dropped section would still clear 10, so §4's
  capture/connection/message pin and §8's printed image are the real "did it run" guards
  and the floor is the fixture-less backstop),
  `toolkit/authsrv/test_chatdefs.py` (the chat echo — `studies/chat/FINDINGS.md`'s
  decode turned into a consumer. The framing check that matters is run against
  **ArenaNet's bytes, not ours**: it pulls the multi-part advert out of live capture
  `20260817T183756`, extracts the literal text, re-frames it with `chatdefs.all_chat_body`
  and requires the result byte-identical to the joined retail body, **fragment
  boundaries included** — which is also where the cap is pinned at **121 units, not
  the 122 the field width and OpenTyria both suggest** (121 = declared − 1, charstore's
  exclusive-cap rule arriving on a second field). The same section re-runs the
  sender/body cross-check at n=1 (playerId 4 → a `0x0059` name) so the decode the arm
  rests on cannot silently rot. The dispatch half calls `_handle_chat_send` with a
  recording send: `!text` must produce CORE fragments then LOCAL `[pid, 3]` **in that
  order** (the tag commits the buffer, so tag-first renders an empty line), `/bow` must
  produce the observed `#1687 #13 #pid` on SERVER `[pid, 6]`, and every other command,
  sigil and the empty string must send NOTHING — six refusal rows, each asserting zero
  sends, because a refusal that echoed anyway would put invented bytes on a measured
  channel. Everything the arm can emit round-trips through the real codec. Needs
  `vault/captures/live/` for the retail section; floor 28 of a 33-check green run),
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
  `toolkit/authsrv/test_fogrle.py` (the fog-init pair's SYNTHETIC stream — the
  2026-08-24 durable fix for the M-key crash (`GmMapView.cpp(1731)`, minimap
  FINDINGS 6f.2, the RUNBOOK failure table's `key:m` row), where `authsrv.py`
  now sends 0x008B+0x008A at map load with an all-fogged RLE built by
  `fogrle.py` instead of leaving `mapDims` 0. The referee is §1 and it is not
  ours: the decoder runs over the VERBATIM ArenaNet payload the probes replay
  and must reproduce the band chain `(0, 22, 0, 0, 0, 0, 0, 0)` closing at
  exactly 38, the 1,004-bit run sum, AND the two block states the client
  itself corroborated behaviourally in 6f.4 — (30,24) SET, (26,22) CLEAR.
  Those two also pin the CONTESTED colour-start (the instruction trace of
  expander 0x00817550 reads fog-first; only reveal-first satisfies the
  client's demonstrated bitmap; FINDINGS 6i) from both sides: the behaviour
  model passes, the static rival is required to INVERT both, so a silent flip
  of `fogrle.FIRST_COLOUR` goes red. The all-fogged default is checked to be
  all-fog under BOTH models — the crash fix does not wait on the contest.
  Encoder properties (additive 0xFF run bytes with explicit terminators, full-
  band coverage landing exactly on the dword flush), the client-derived
  refusals (dims.x % 32 is ChCliApi:77's own assert), LE dword packing pinned
  against 9 of the replay's 10 dwords, >64-dword chunking for the
  accumulating handler, both messages' wire shape through the real codec, and
  the `fog_init_for_map` content join — map 148 gets continent 1's observed
  (64, 128), a continent with no observed dims is REFUSED by name rather than
  guessed (a wrong pair is the same crash), FOG_INIT defaults ON. 41 checks,
  floor 41, ~2 s),
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
  .raw, which closes R0a's standing caveat. §5, added 2026-09-01, pins a second thing a
  capture must be able to say: **which configuration produced it.** Two behaviour defaults
  shipped and were reverted the same day, and identifying which of six 35-second sessions
  had actually run them cost an hour of inference from send labels — `attack_stopped`
  being absent was the only tell, and it only ever identified one of the two flags. The
  header carried build, world, map and account uuid and not one line of configuration, so
  every A/B this project has run was self-identifying by luck. `Recorder.__init__` now
  emits a `flags` record built by `capture_flags()`, which **discovers** every
  SCREAMING_CASE module global rather than hand-listing them — a flag added tomorrow is
  recorded tomorrow with nobody remembering — and reads the LIVE globals, so a flag set by
  any route and not just argparse is caught. The load-bearing check is the one that can
  fail: flip a real flag and the census must move, then prove the probe restored it. Floor
  4 → 10, because §5 is fixture-free and runs on a bare machine; 16 with a vault),
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
  `toolkit/authsrv/test_smsgnames2.py` (**two more GAME_SMSG names, 2026-08-22
  round 2 — the held player-record/agent pair, earned by reading the consumers**;
  the binary-side claims live in each overrides `why`, this pins the wire. §2:
  `0x003C PLAYER_UPDATE_FLAGS` — ≥1,393 corpus messages, and the MASK (field 3)
  is **7 in every one** (the 3-bit flags word), the VALUE never sets a bit outside
  the mask (consistent with `(old & ~mask) | value`, not an arbitrary write), and
  89 distinct playerIds are addressed (keyed by player). §3: `0x003E
  AGENT_VIEW_UNLINK` — ≥65 messages, each a single agent id, and 0x0021
  WORLD_REMOVE_AGENT outnumbers it **2,253 to 65**, which is the critic's
  narrowing made concrete (a view unlink is not the world despawn). `0x008D`
  MAP_MARKER and `0x00B0` stayed HELD — no ArenaNet naming string and no named
  consumer, recorded in studies/smsgnames §10 rather than promoted on inference.
  Needs `vault/captures/live/`, §1 runs bare; floor 9),
  `toolkit/authsrv/test_itemdetail.py` (**the five GAME_SMSG names of the 2026-08-22
  static pass — ITEM_LOW_DETAIL/ITEM_HIGH_DETAIL, the equip-set pair, and
  AGENT_SET_MODEL_SCALE — held to what a `.raw` can arbitrate**, so the corpus can take
  a name back; the binary-side claims (the builder `0x848450`'s field map, the
  IsDetailHigh bit, assert text) live in `studies/smsgnames` §9 and each overrides why,
  not here. The invariants: ZERO `ITEM_CODE_TERMINATOR` dwords arrive across all corpus
  code[] words — ItemCode:516 REFUSES a wire terminator and the client appends its own,
  a prediction with no free parameter; `0x0161`'s declared field 14 is absent from every
  retail message (the format table declares a slot retail never fills); the fileId
  deferred-fetch top bit rides ONLY the high-detail stream; the server streams the
  COMPLETE four-set equip table (four indices in equal counts, never partial) with every
  set index under the client's own `ITEM_PLAYER_EQUIP_SETS = 4` bound, every inventory
  key declared by a prior 0x0144 and every non-null item ref by a prior declare; and
  every `0x009A` value is a pure top-byte scale percent — the packed word's UPSTREAM
  hue/sat/lightness low bytes never arrive on retail, 100% dominant (CpsMonster's no-op
  case). Counts are pinned as floors so the pins survive corpus growth; the A-only/
  B-only pair asymmetry is printed, deliberately not asserted. Also ties the names to
  the invariants: section 1 goes red if `schema/overrides.json` renames or drops any of
  the five. Needs `vault/captures/live/`, skips declared if absent; floor 19),
  `toolkit/authsrv/test_wearmap.py` (**the wear mapping — equip slot / wire item type /
  composite record, and WHICH of the three places a piece on a body**,
  studies/playercomposite §9.2's answer to §2 step E, proved four ways. §1 exercises
  `wearmap.py`'s own tables and EVERY refusal direction — a composite flag in a hand
  slot, an armour type in a hand slot, an unprecedented (slot, type) pair, a
  non-composite body piece, a record type the wire type never pairs with — plus the
  accepts that matter (a non-composite head item IS legal: the 132 festival masks; the
  measured legs-on-Boots anomaly IS legal). §2 is the exe cross-witness in
  `test_playerassembly` §7's pattern: `wearmap`'s transcribed 42-entry attach-class
  table and per-class attach codes must EQUAL `composite.py`'s anchor-located
  extraction (`_attach_class`, one image-wide parse or a refusal), and Head's two
  record types must land on two distinct components through the exe's own
  `s_components` — the shape a type→record function could never express. §3 is the
  wire census: ≥6,445 declares / ≥5,709 worn joins with every worn item declared
  first, every body-slot (slot, type) pair inside `WORN_TYPES` (the table IS the
  corpus), every hand wear an attachable type — the classifier read from the exe
  holding against wire it never saw — slots 2–5 composite in 100% of wears, the head
  slot splitting ≥658 composite / ≥132 attach under ONE wire type (the flag
  discriminates, never the type), and the three-leggings anomaly pinned (slots 3/4/5
  of one agent, capture 20260817T231139 — the slot is a hanger). §4 is the archive
  join: flags bit 2 ⇔ fileId-indexes-the-CpsData-table with ZERO mixed cells
  (5,528/181), wire-type→record-type sets EQUAL `RECORD_TYPES_OF_WIRE` both ways, the
  many-to-many counting proof (16→{17,19} at ≥435/≥223; 15←{7,44} at ≥1,153/≥97), and
  the five STARTER_ARMOUR rows passing the full triple check — the same validation
  `authsrv.py` runs at import so an authored row that would draw on the wrong body
  part dies at the desk. The 5,709 floor carries its own correction: an earlier census
  said 5,710, having misread a `0x006F` UNEQUIP through an order-probing heuristic;
  the field order is now the handler's own. **§5 is the TYPE-45 TAXONOMY**, which
  closed the composite arc's last open item at a desk (§9.24): it pins that all
  **29** costume-head records are record type 17 or 19, that the COMPONENT is a
  function of the record type ALONE (`{17: {2}, 19: {1}}`, no exceptions), and that
  all 29 resolve geometry for BOTH sexes. That second check is the whole closure --
  a component comes from `s_components[hdr>>22]`, a field of the RECORD, so no
  property of the table's layout (which five-record run an id belongs to, the thing
  §9.10 sorted them by) can reach the dressing path at all. The fourth check exists
  to stop the other three agreeing vacuously: **3 of the 29 carry NO per-sex base
  slot** (`SEX_BASE_SLOT = (0, 5)`) and resolve only through `SHARED_SLOT = 10`, so
  a census reading a different archive, or a `base_file` that stopped falling back,
  would find none of them and quietly pass everything else. The census that produced
  this was WRONG TWICE on the operand before it was right -- it read only opcode
  `0x0161` when costume heads are declared under `0x015E` (caught by its own
  pre-registered positive control, which printed "not measuring the thing" rather
  than a census of nothing), then scored "run" as membership of a section-1 LIST
  CELL, which every record is in. Needs `vault/captures/live/` for §§3–5 and the
  study archive for §§4–5, skips declared; a whole green run is 40 and the floor is
  **20**, its MANDATORY CORE -- lowered from 36, which sat above it, so a machine
  without a vault would have failed on the shortfall instead of reading the skip the
  vault block already declares),
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
  `toolkit/clientscan/test_skillsentinel.py` (**the duration-slot sentinel
  `0x20000` is ENERGY UPKEEP, in ArenaNet's own word** — studies/skills §13
  left "what the enum means" NOT FOUND and §13.1 answered it. §1 pins the
  server-side name (`effects.DURATION_ENERGY_UPKEEP`, `sentinel_name`, and the
  `resolve_duration` refusal that now names upkeep) with no vault. The static
  witnesses (pinned exe): the image asserts `hasEnergyUpkeep` in
  `GmCtlSkCard.cpp` (and `GmCtlSkListEntry.cpp`, a second control), the full
  assert is `!(hasEnergyUpkeep && skillData.healthSacrifice)`; the bytes by
  that assert are `mov eax,[esi+0x44]` (the duration slot; esi is a skill
  record) then `cmp eax,0x20000` — an EXACT compare, so `0x30000` does not
  match; and in the full 3,443-row table all 27 skills carrying `0x20000` are
  Enchantments while `0x30000` spans 16 types (a no-duration default, not an
  upkeep marker). Needs the pinned exe for §2–4, §1 runs bare. **Floor 4,
  lowered from 11 on 2026-08-30 and MEASURED, not reasoned**: with `RURIK_VAULT`
  pointed at an empty directory the bare run is **4 checks, 1 declared skip
  ("static witnesses"), rc=0**; a whole green run is still 11. The old 11 was the
  whole run rather than the mandatory core, so a machine without the vault went
  red on `ONLY 4 OF A DECLARED FLOOR OF 11 CHECKS RAN`, which names the wrong
  thing — nothing failed to execute, a section declared itself absent. Before the
  same day the bare path never ran at all: `pinned.find()` raises `SystemExit`,
  `except Exception` did not catch it, and the file died with rc=1 and no verdict.
  Same correction `test_compositetrap.py` took, 80 → 78),
  `toolkit/clientscan/test_typenames.py` (**WHAT THE CLIENT CALLS EACH SKILL
  `type_code` — from the client's own switch, not from a wiki**.
  `studies/presearing/MANIFEST.md` §8 named ten of the thirty codes by Rosetta
  stone — pick skills whose type is known from outside, read their `+0x0C` —
  and left **eleven UNKNOWN**; `PLAN.md` §8 item 5 singled out **16** because it
  sits on this server's own default bar. None of that Rosetta work was
  necessary: the namer at `0x004F9BF0` reads `[skillRecord+0x0C]` and hands it
  to a 29-case switch at `0x004F9DD0` whose every case computes a **string id**,
  and whose default arm logs ArenaNet's own sentence *"There is no string to
  describe skill %u's type."* — which is the strongest single piece of evidence
  that this is the type namer and not some other switch on some other field.
  **§4 is the whole argument and it is a control, not an assertion.** The index
  bias is the only free parameter in the derivation, and at `type_code - 1` all
  **ten** independently-named codes resolve EXACTLY to the ten words that
  document already used — then the same check is re-run at bias 0 and 2 and must
  score **zero**, which it does. Without that second half the ten agreements
  could be a table of plausible words meeting plausible guesses; with it, one
  step either way breaks every known code at once. The exactness is load-bearing
  and was learned the hard way: the first cut asked `expected in got`, and
  `"Spell"` is a substring of `"Hex Spell"`, so the control leaked a false hit
  and went red on its own weakness rather than on a real agreement. §3 reads the
  switch as **arithmetic** — bias from `dec eax`, bound from `cmp eax,imm8`,
  default from the `ja`'s rel32, table from the `jmp [eax*4+imm32]`'s imm32 —
  then walks all 29 entries against the pins: 25 agree and exactly the four
  special codes land on the default arm, each for a *different* reason (14 is
  intercepted upstream because an attack's name depends on the weapon; 17 and
  18 are refused on purpose and return the null record; 22's name is not a
  constant at all). **§5 answers item 5**: type 16 is displayed as **"Skill"** —
  and so is type 10, from a **different string record**. Both halves are
  asserted, because same-id would mean our decode collided and a different word
  would mean 16 is a type nobody has heard of. §5 also pins the *address* of
  16's arithmetic, `0x004FA34B`, deliberately: the agent that first found this
  cited `0x004FA2F9`, which is the tail of the type-20 case — right conclusion,
  wrong citation, and a wrong citation is what makes a later reader's audit fail
  and look like the claim failed. **IDS, NOT WORDS, ARE WHAT THE MODULE STORES**
  — CLAUDE.md's "commit the id, resolve the string at run time from the owner's
  own archive" — so §§1–2 run on a bare machine and the archive half declares a
  skip. Floor 6 of a 16-check green run. ~4 s),
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
  `toolkit/authsrv/test_armour.py` (**the armour RATING** — 19 checks with the vault,
  15 without, floor **15**; it read "16 checks, floor 16" until 2026-08-27. **§2 now
  scores `probes.py`'s item ids against the server's minted set, and it went RED on
  two live collisions before either constant moved.** The `reserved` check had
  existed since the section was written and was pointed ONE WAY ONLY — it scored
  `STARTER_ARMOUR` against the server's own ids and never read `probes.py`, which
  mints item ids of its own and declares them onto the SAME client through the SAME
  `0x0161`. `_ARMOR_LEGS_ITEM` was **2**, which is `BACKPACK_ITEM_ID`; and
  `_ARMOR_BOOTS_ITEM` was **3**, which is `warrior_body`. Neither failed anything at
  run time — a second `0x0161` for an id the server already declared overwrites the
  client's record rather than erroring — so the armour probe was silently
  re-declaring the backpack and the chest on every run, and any reading through it
  measured two writers at one slot. Now 43/44, joining `_DRAIN_ITEM_A/B/C` in that
  module's existing 40s band rather than the 10/11 sitting flush against the
  server's block. The ids are gathered **from the module** rather than re-listed, so
  a fourth probe item is covered automatically — that is the exact way the gap
  survived. **Three bugs surfaced behind this one and all are fixed here.** (1) The
  first scan required a name ENDING in `_ITEM` and read 2 of the 5, missing
  `_DRAIN_ITEM_A/B/C` — caught on its first run by the vacuity guard sitting beside
  it, which is the whole argument for putting one next to a filtered search.
  (2) §3's no-vault path had **never executed**: `vaultpath.require_dir` reports a
  missing vault by raising `SystemExit`, a BaseException that sails through
  `except Exception`, so a bare machine did not skip — it died with no verdict, while
  the docstring promised "sections 1, 2 and 4 hold with no vault". `test_quests.py`
  §19 carries the identical note. (3) Past that, the `skip()` call passed **one**
  argument to a two-argument signature, so the moment the except caught, the skip
  itself raised `TypeError`. Two stacked bugs in a path nothing exercised; both found
  by pointing `RURIK_VAULT` at an empty directory, which is the one-line way to test
  a no-vault claim. **The floor moved DOWN, 16 → 15, and that is the repair rather
  than a retreat**: 16 was the with-vault count of the day it was set, so the bare
  machine the docstring promised would have been called incomplete — it never got to
  prove that, because the run died first. Six deliberate breaks redden §2, including
  a collision planted on the `_DRAIN_ITEM` ids and the scan itself going blind).
  `studies/character/FINDINGS.md` §2 asked on 2026-08-06 where an item's armour
  rating lives and proposed the experiment that would answer it: send the
  warrior chest and read the rating off the client's own tooltip. It sat open
  for a fortnight because it was TWO problems wearing one coat — the modifier
  words were opaque until 2026-08-20, and **this server was not sending the
  armour at all**, so the character stood in every capture bare-chested and
  there was nothing to hover. Decoding alone would not have closed it.

  §1 requires all five pieces to carry identifier **572** with argument **25**
  (the rating) and the chest to carry **527** arg 20 beside identifier **4**,
  whose only string is 2480 `vs. physical damage` — the pair the client renders
  as `Armor +20 (vs. physical damage)`. §2 checks the plumbing that had to
  exist for any of it to be visible: the equipped-bag slots are retail's
  MEASURED ones (Body 2, Boots 3, Legs 4, Gloves 5, Head 6), the five item ids
  collide with neither the weapon, the Backpack nor the purchase namespace, and
  the burst reads the constants rather than repeating slot numbers.

  **§3 is the check worth having and it is not about our code.** These rows came
  from OpenTyria's hand-written `GmDefaultArmors`, and `content/items.toml` said
  in place: *"no capture of ours has ever carried these bytes."* Our own vault
  refutes it — ArenaNet sent `0x0161` declarations for all five of these exact
  model ids, **nine sightings each across three captures**, and §3 requires every
  fixed field AND all three modifier words to agree. `dye_colors` is compared as
  MEMBERSHIP, not equality, because it is what a player dyed that instance and
  retail shows four values for one model; requiring equality there would report a
  real agreement as a mismatch. §4 is the control: armour on by default, a
  `--no-armour` flag that empties the doll, and a check that no piece ships with
  an empty modifier list — which is the "renders and protects nothing" state the
  study named.

  `toolkit/clientscan/test_itemmods.py` (**the item-modifier decode, who reads
  a modifier, and the attribute bonus** — 37 checks, floor 37; this line read "28
  checks, floor 28" until 2026-08-27, when the file itself declared 37. **§10's
  attribute-bonus count is a FLOOR and was an equality until the same day, when it
  went RED ON CONFIRMING EVIDENCE**: nine later live captures took the corpus from 26
  words to 38 and all twelve new ones carry the same `(543, stacking, attr 20, +1)`
  signature, so the claim strengthened and `len(bonus_words) == 26` called it a
  failure. The count pinned the size of the vault, which nothing here measures. It is
  `>= 26` now with the signature set carrying the claim — the floor guards vacuity,
  because an `all()` over an empty list is True and a corpus that stopped loading
  would have passed silently. Both mutations redden it: an emptied corpus and a
  planted stray signature). Every item on the wire carries a list of 32-bit modifier words, and
  `studies/character/FINDINGS.md` called them "the largest hole" three times: armour
  rating, damage range and every "+15% while…" line live in them and nobody had
  decoded one. `itemmods.py` reads the format out of the client's own parser —
  `{identifier: bits 29-20, arg: bits 17-8, arg2: bits 7-0}` plus two skip
  predicates — and dumps the identifier vocabulary by walking each of the 133
  dispatch handlers for the TEXT IDS it formats its line through.

  **Two checks here can refute the layout and neither has a free parameter, which
  is the whole reason this file exists.** §2 decodes words whose rendering this
  repo has already watched on a caged client (`Armor: 25`, `Armor +20 (vs.
  physical damage)`, a Backpack that holds twenty items) and requires the argument
  field to equal the number that was on the screen. §4 runs **every modifier word
  ArenaNet ever sent us** — 5,266 of them across 1,781 item declarations in 13 live
  captures — and requires every identifier to be one the client actually
  dispatches: a wrong shift or mask scatters identifiers across the 10-bit space
  and most miss both jump tables. The observed answer is **5,266/5,266 over 35
  distinct ids**. §4 declares a SKIP without the vault rather than passing on no
  data, and §5 blanks the anchor bytes to prove the tool REFUSES instead of
  reporting an empty vocabulary — which would read as "this build has no item
  modifiers", the shape of every silent-zero bug in this repo.

  **§6 and §7 answer a different question: who reads a modifier the tooltip
  renders NOTHING for.** `ItemName.cpp` sends 21 of its 157 dispatch slots to the
  walker's loop tail, and the two busiest identifiers in the wild are among them.
  §6 pins that count at 21 — it was 22 until the detector was fixed, because the
  last renderer in the chain falls through into the tail, and identifier 526 would
  have been published as "the client draws nothing for it" while it pushes string
  2387 and calls TextApi. §6 then reports that **633 is read by two literal
  compares outside the walker and 617 by nothing at all**, and those two checks
  sit together on purpose: the positive one is the control that makes the negative
  worth anything, which is what `studies/enemy` §6o lacked when it reported a
  field as having no writer. §7 takes **570 chances** to refute what 633 turned
  out to be — every argument must be a real attribute (`< 51`, from
  `attribtable.py`) and every second value a reachable rank (`1..12`, from
  `attribpoints.py`), two tables this file does not extract; and the attribute
  must be constant per item model while the rank varies, which holds on 63 models
  and 0 exceptions.

  **§8-§10 are the attribute BONUS, and they are here because of how the search
  for it failed first.** `studies/itemmods` had recorded "exactly two handlers
  treat their argument as an attribute index" — a count taken from the two
  asserts naming `attrib < CHAR_ATTRIBS`, from a tool that prints in its own
  output that its module lists are a FLOOR and not a census. §8 asks the right
  question instead: which handlers resolve an attribute NAME through
  `s_attrib`? It locates that accessor **by shape** — four one-line field
  readers with a stride-20 `lea`, of which the lowest displacement is the table
  base — so no build-specific address is involved, and the answer is
  **fourteen**, the same fourteen on all three builds. Two of them render
  `<attribute> +N`: **543 Stacking** and **542 Non-stacking**.

  §9 is the check with no free parameter: compose 543's word from its four
  fields and you get `0x21F01401`; ArenaNet sends `0x21F81401`. The difference
  is **bit 19**, one of three bits the walker never reads and which §10 measures
  to be constant per identifier across all 5,266 corpus words (35 identifiers,
  0 exceptions). §10 also replays all **26** attribute-bonus words the corpus
  holds — every one `Swordsmanship +1` on one item type, all carrying an armour
  rating — and requires the composer to reproduce each exactly.

  §11 guards a duplication that was introduced ON PURPOSE. `content/items.toml`'s
  starter hammer now carries a real 543 word AND a declared `attribute_bonus`,
  because the run showed they drive different surfaces — the word draws the
  tooltip, the field feeds the server's `0x003A` effective column. One fact in
  two places is the shape of bug `studies/pvpui` §34.5 is about, so §11 fails if
  they ever disagree and has a control that bends the field to +2 to prove it can
  go red.

  **§12-§14 are what turn "nothing reads 617" from an absence into a
  measurement.** §6 above reports the negative with a positive control, which is
  the right shape and still not enough: a search that comes back empty says
  nothing about whether it had anywhere left to LOOK, and `studies/enemy` §6o
  closed a question for a whole session on exactly that footing and was false.
  §12 bounds it. To read an identifier the client must isolate bits 29-20; x86
  leaves two ways to do that, both fixed byte sequences; an exhaustive scan of
  `.text` finds **sixteen** such sites in a ten-megabyte image, naming eleven
  identifiers between them, and 617 is not one. The check also requires the
  **158** further mask sites that are NOT modifier code to be counted rather than
  filtered away — `0x3ff00000` is also a double's exponent mask, and a scan that
  dropped them silently would be reporting item code while claiming to report an
  instruction. §13 requires the identical census on all three builds, because a
  negative that holds on one build could be that build's quirk.

  **§14 is the positive half, and its control is the point.** An absence is hard
  to build on, so the corpus is asked what 617 IS: its `arg2` is single-valued
  for **71 of 71 `model_id`s** over 420 words. That would be worth nothing alone,
  because any field with small enough groups looks deterministic — so the second
  check requires the item's FILE id to FAIL the same test, which it does (5 of 34
  carry more than one value). The study's earlier "constant for 29 of 34 item
  model ids" was the file id under the model id's name, and §14 is what corrected
  it.

  The floor was 12 because 14 was declared, 12 executed, and the ledger refused
  the run — the guard doing its job on the file that documents it. It went to 19,
  then 28, then 30, then 37, each time read off the green run rather than
  predicted.

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
  `buildid.of_image()` now, the row names WHICH image, and the control is a
  payload built from an unidentified path that must record `None`. **That
  control was one case short until 2026-08-17, and the bug it missed was live
  the whole time.** The fix had read `build = pinned.BUILD if kind in
  ("pristine", "patched") else None` — the constant, guarded by a check that the
  file is SOME recorded build rather than THE build — so pointed at the vaulted
  38833 client it scored `pristine` and stamped 38797 on every row, beside an
  `image` string reading "build 38833, as ArenaNet shipped it". The row
  contradicted itself and the test stayed green, because the only negative it
  had was a path naming no file at all: a control for "unidentifiable" is not a
  control for "identified, and not the one you assumed". §7 now emits from every
  other build the vault holds and requires the row's `build` and `image` to name
  the SAME one. Three sibling tools had the identical defect that day
  (`framebus.py`, `consttable.py`, `heroes_table.py`); the shared helper is
  guarded by `test_buildid.py` §5. One check was
  also DELETED as one that cannot fail -- `ar.row(n).index == n`, which
  `archive.py:367` asserts internally and would have raised first -- and
  replaced by two the archive can refute. THREE scores, each measured and none
  subtracted: **77 with client and archive, 64 with the client alone, 39 with
  neither** -- floor 77, so a vault-less run goes red. (79 since 2026-08-17
  where the vault also holds a build that is not the pin; the floor stays 77
  because those two declare a skip without one.) The archive section
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
  `toolkit/clientscan/test_srctree.py` (the Cli/Srv source-tree split, on EVERY
  vaulted build — and it proves its own negative result can go red first. Since
  2026-08-12 it takes the STAMPS from `pinned.BUILDS` rather than spelling
  them again, and a build added to that registry with no expected path count here
  FAILS rather than being skipped: this is the only cross-ArenaNet-build test in
  the tree, so an unmeasured build sitting in the registry would leave it claiming
  a coverage nothing provides. That refusal is the shape `test_msgshape.py` and
  `test_avevents.py` were given on 2026-08-29, when 38849 reached the registry
  and those two died on a bare `KeyError` while this one named the build and
  carried on. 38849's own row was measured by running this test's `source_paths`
  over the image: 937 paths again, zero server-side translation units, the same
  two client-side `Srv`-named files, the same twelve Cli-split subsystems and one
  PDB path naming target `Gw`. Three consecutive builds now agree, which is the
  census HOLDING rather than the check going quiet — every one of those five
  figures is re-derived per build. Floor 48 (39 + 9 for the third build)),
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
  **§5 guards `of_image`, added 2026-08-17, and it exists because "which build
  is this file" had no single answer and four tools invented one.**
  `pinned.identify()` returned the CATEGORY — `"pristine"` — and threw away the
  row it matched, so a caller that had just identified a file correctly still
  had nowhere to get its number and reached for `pinned.BUILD`. All four did:
  `framebus.py` printed "the pinned build 38797" over the vaulted 38833 client
  (its label was `len(blob) == pinned.SIZE`, and 38833 ships at *exactly*
  38797's 10,483,904 bytes, so the size check could not tell them apart), while
  `worldmap.py`, `consttable.py` and `heroes_table.py` stamped 38797 onto
  extracted content rows — where condition 2 of the owner's ruling says the
  build is the thing that makes a row re-derivable, so re-deriving one against
  the build it named would have read a different table. `worldmap.image_build`
  is the one to read: its docstring says "Never a constant" and it emitted
  `build: 38797` beside `image: "pristine: build 38833"`, contradicting itself
  inside every row for three days with a green test over it — its control
  covered an image that could not be identified AT ALL and never one that was
  identified as a build that is not the pin. `pinned.identify_build()` now hands
  back the matched row, and `buildid.of_image()` is the one call for a build a
  tool prints or emits: registry sha256 first, the client's own build getter as
  the fallback that answers for an image `BUILDS` has never seen. The checks are
  written to fail against the old code rather than merely to pass against the
  new: each non-pinned build must read as ITSELF *and* must not read as 38797,
  because a label printing both is still the misreport.
  **§5's fallback fixture MOVED on 2026-08-19 and the section went red on the
  way**, which is worth recording because the red was correct. It named our
  patched 38833 copy, `vault/run/2026-08-13_64fae3b1369b/Gw.exe`, on the strength
  of "`patched` is None for that build" — true when it was written on 2026-08-17,
  false two days later, when `pinned.BUILDS` gained a patched digest SET and that
  file's `e06ada3b…` was committed into it. `identify_build` now answers
  ('patched', 38833) where the section pinned ('unknown', None). The CASE — a real
  client of a build we hold, sitting in no registry row, where only the image's
  own getter can answer and stamping the pin is pure invention — is unchanged;
  only the file that still fits it moved, to `vault/run/reskin-roster/Gw.exe`,
  the reskin experiment copy that `register_patched`'s sanity bound refuses (682
  bytes in 211 runs) and that nothing has ever filed. **What that fixture cannot
  pin is said out loud in the file**: reskin-roster IS 38797, so the NUMBER no
  longer separates "read from the image" from "answered with the constant" — both
  are 38797. A third check does the separating instead: the `why` must name the
  image's own build getter and must NOT claim a registry row, which is exactly
  what an implementation returning `pinned.BUILD` could not say. Reverting the
  repoint reddens all three.
  Needs the vault. Floor 39 (was 29; §5 adds 12, of which 3 ride on
  `run/reskin-roster/Gw.exe` and declare a skip — 42 on a full vault, 39 on a
  vault holding only the pristine snapshots, which is the mandatory core), ~8 s),
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
  `toolkit/clientscan/test_codedstr.py` (the coded string — markers, and
  `0x100`-biased base-`0x7F00` varints — and `studies/quests/FINDINGS.md` §3.2's **66 of
  66** turned from a paragraph into a check, which §7.9 asked for by name. The rule was
  derived in `studies/textrec/FINDINGS.md` §4 from `TextParser.cpp` and then tested in
  quests §3.2 against 66 EncString slots on ArenaNet's own wire — a source the textrec arc
  never had. Every authored quest string this repo sends is built on it and every string
  id it reads out of a capture is decoded with it, so it is load-bearing both ways and
  nothing could turn it red; the ENCODE half lived nowhere at all, so the 66/66 was only
  reproducible by rewriting the script that made it. **§1 runs on a bare machine** and its
  two headline fixtures — `80660 -> 8102 3E14`, `0x3D64 -> 15460` — were written into a
  document BEFORE this module existed, so they cannot have been back-fitted. It also pins
  the digit boundaries (`BASE-1`/`BASE`/`BASE+1`, where a carry misusing `0x8000` or
  `0x100` shows up), that a sub-`BASE` id is ONE word (an always-two encoder round-trips
  fine and does not match ArenaNet's bytes), and four refusals — including a MARKER word,
  which is the client's own distinction: a `0x004C` description beginning `'S'` (`0x53`)
  killed a real client on `TextApi.cpp:585` asserting that bound. **§3 is the one worth
  reading.** All 66 slots resolving is weak — a wrong rule also produces numbers. What is
  strong is that they PARTITION: slot 0 plain 22/22, slots 1 and 2 encrypted 22/22, which
  is textrec §4's own prediction confirmed on a source it never had; under a wrong reading
  the plain share would sit near the archive-wide ~28%. Its CONTROL is the rival raw-word
  reading, which could have won and did not — `0x3D64` is 15460 our way and 15716 the
  rival's, one plain and one encrypted with a key this repo has not recovered. **A first
  draft asserted the rival record was ABSENT and went red**: §3.2 says "an encrypted
  record returning nothing" and the nothing is the decoded TEXT — the assertion was
  stronger than the evidence, not the document wrong. **No ArenaNet text is asserted
  anywhere**, deliberately: the structure discriminates and the word is their expression.
  Verified by sabotage — `BIAS=0` fails 8 checks, `BASE` and `CONT` changes raise. The two
  captures are NAMED, not globbed, because the vault's capture tree is append-only and a
  glob would silently move the denominator, which is what put `test_smsgsweep` red at 177
  opcodes the same week. Floor 12 against a run of 18 — §2 and §3 need the corpus and the
  owner's archive and declare skips. ~10 s),
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
  is an artefact rather than a finding. **§3 reads the tool's own header, added
  2026-08-17, because the label lied.** `--exe`'d at the vaulted 38833 client
  this tool printed "the pinned build 38797": the label was
  `len(blob) == pinned.SIZE`, and 38833 ships at *exactly* 38797's 10,483,904
  bytes, so a size check cannot separate them — `pinned.py`'s own `BUILDS`
  comment had written down two days earlier that "a size check written anywhere
  else is now a bug". This is not cosmetic. Addresses drift between the two
  builds by 0x20..0x160 per region, so every VA below that header is 38797's
  offsets applied to another build's bytes, and `studies/pvpui/FINDINGS.md`
  §4/§15.0 records two wrong-build readings from this session that each produced
  a confident wrong answer, one nearly published as a correction. §3 runs the
  CLI as a SUBPROCESS — the defect lived in `main`'s print statement, so
  anything importing the module and asking it directly would have stayed green
  while the command line kept saying 38797 — and asserts the header names the
  file, reports THAT file's build, does NOT claim the pin (the negative control:
  a label reading "38833 (the pinned build 38797)" passes a check for "38833"
  and is still the bug), and warns that the VAs were not measured on it. A
  positive control on the default run stops a fix that calls everything
  not-the-pin. It needs a SECOND real client and skips without one, which is why
  the defect survived: against the pin the constant is correct. Same shape in
  three other tools that day — `worldmap.py`, `consttable.py`, `heroes_table.py`
  — all routed through `buildid.of_image`, with the shared helper guarded by
  `test_buildid.py` §5. **2026-08-19, the COMPLETION FAMILY joined the check**
  (`studies/quests/FINDINGS.md` §9.7): §9.3's four unattributed publishers of
  GmQuestComplete's band turned out to be the other four completion-family
  opcodes' own bodies — `0x006C`→`0x10000156`, `0x0096`→`0x10000158`,
  `0x0097`→`0x10000157`, `0x00FB`→`0x10000159` — and §1 now asserts the
  five-id closure and the `0x0096`/`0x0097` SWAP structurally (the one detail
  an assume-adjacent reading gets wrong; an edit that re-sorts the pairing into
  opcode order goes red), while §2 re-reads both from the pinned image via
  `completion_family()`. §1 runs on a bare machine — `framebus.py`
  is a fixed-byte-pattern tool and takes no disassembler — and §2 and §3 each
  declare a `LEDGER.skip` without the vault, which is why the floor is 16 and
  not 27. ~4 s),
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
  `toolkit/clientscan/test_heroes_table.py` (`s_heroClientData` as content
  rows, and the trap it exists to avoid. `s_titleClientData` sits SIX
  INSTRUCTIONS from it -- accessor `0x005A9350` (`cmp esi,0x30`, stride 12)
  versus `0x005A9380` (`cmp esi,0x28`, stride 24) -- and this arc lost a
  contested reading to exactly that adjacency until the client's own assert
  strings settled it. A structural locator that closes on the wrong anchor
  still closes, so the failure mode is not an error but a clean, plausible,
  WRONG table of numbers presented as heroes. §1 pins the geometry and the
  closure the artifact can refute: the table must end on the byte where its
  anchor string begins (`base + 40*24 == anchor_off`), which an off-by-one-row
  base or stride does not satisfy. §2 checks the index column equals the row
  number on all 40. §3 is the sabotage: `table_for` is monkeypatched to hand
  back the title table's 48 x 12 geometry and the extractor must REFUSE with a
  message naming the trap, followed by a positive control that the real table
  still loads -- otherwise §3 would prove only that `load()` always raises.
  §4 runs the emitted TOML through `content.py`'s REAL `_check_provenance`,
  all 40 rows, then strips `extractor` from one and requires a refusal, so the
  40/40 is a result rather than a tautology. **§4 also pins that the row's
  `build` is the build it was READ ON, added 2026-08-17**, because it was
  `pinned.BUILD` and every row from every client claimed 38797 — and the gate
  above passed all of them, since `_check_provenance` asks that a build be
  PRESENT, not that it be true. Only `--exe` at a second real client separates
  the two, so that is what it does: rows emitted from the 38833 client must be
  stamped 38833. `consttable.effect_toml` had the identical defect and
  `test_consttable.py` §8 now checks it the same way; both refuse to emit at
  all when `buildid.of_image` cannot name the build, rather than writing the
  usual answer. §5 pins that `--resolve` with no
  explicit rows is refused: ids ship, English does not, and a committed column
  of resolved names is the bulk expression the provenance gate refuses. Needs
  the vault; SKIPs with its reason. Floor 10 (12 checks with a second vaulted
  build), instant),
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
  `toolkit/clientscan/test_noclipscore.py` (**the no-clip scorer's PLANE channel,
  and the blind spot that cost it two no-clips**). `noclipscore.py` came out of the
  obstacle dig (FINDINGS §1x) and reproduced r4a's numbers exactly — then read
  **section A: 0 off-mesh** on `r5bridge`, a capture the operator took *because* they
  had just walked under a bridge twice. `containing(x, y)` UNIONS ALL 68 PLANES, so a
  body on a deck and a body on the ground under it are the same query and both score
  on-mesh. FINDINGS §1w.7 had established plane-blindness is irrelevant to a carved
  HOLE — true, and precisely what made this look settled; a bridge is the other case.
  So this file holds section C to three properties the old code fails: an anomalous
  sample is **reported**; **section A stays blind to that same sample**, which is what
  proves the two sections measure different things rather than one restating the other
  (the two-instruments-one-theorem trap); and a run with no stacked geometry says
  **ZERO EXPOSURE in those words** rather than a reassuring zero. A fourth check is the
  control that matters — a body on the plane the mesh DOES offer must NOT be flagged,
  or the detector would report every run as a no-clip. The fixtures are synthetic
  captures over the REAL map-280 mesh built from `readhook._LAYOUTS` (so fixture and
  parser share one description of the record, test_movehook §11's discipline), and
  **each fixture proves its own premise first** — the coordinates came out of a
  capture, so the file asserts the mesh really offers only the plane it claims before
  asserting anything about the detector. Writing it found a second defect: section B
  `return`ed on a capture with fewer than two clicks, which SILENTLY SKIPPED section C
  — a keyboard-only walk would have been scored with the one section that can see a
  bridge missing. **§5 of `test_noclipscore.py` (2026-08-29, FINDINGS §1z-e.1) pins
the same-tick ALIAS**: the
  old section C re-found each sample's plane by (tick, ecx), reading the FIRST record
  at the tick — which erased two real k2-2 anomalies whose own plane differed from a
  same-tick sibling's. The fixture is two same-tick records where the first record's
  plane is legal at the second's point; own-plane scoring flags both, the aliased
  lookup flagged one, and the check was proven red against the pre-fix code before it
  shipped. Under the fixed lookup the published §1z-c counts move deliberately
  (r5bridge 6→8, r4a 5→8, r5 stays 0). Floor 9, 10 on a machine with the archive;
  skips whole if the archive or `sites.h` is absent.

  `toolkit/clientscan/test_planecensus.py` (**the plane census, and the four ways a
  census lies without going red**). `planecensus.py` is `noclipscore.py` section C
  pointed at the SERVER's corpus instead of a movehook capture — 11,754 scorable
  `position_report` rows against a handful — and it answers HANDOFF §D. It made two
  wrong turns getting there, and neither was catchable by reading the diff: it scored
  the `plane_echo` tripwire from `grant_verdict.plane_dest` (a control against the live
  tripwire's own three sessions read **0/0/5 against a logged 4/30/9** and refuted it),
  then read `0x0029`'s trailing dword as ONE u32 and published 15.29% — the dword is
  **two u16s**, and the tell was "we emit plane 1703962", which is `0x001A001A`, the
  label's own "26->26". So the controls are what this file pins. **§1: the mesh pin is
  IN BAND and TOTAL** — every capture names its own mesh via the server's opcode-405
  `INSTANCE_LOAD_SPAWN_POINT(file N)`, no capture names two, and all 12,215 reports
  attribute; the `version` record's `map_id` is 148 in 1,206 of 1,212 files and is the
  LOGIN CONSTANT, so §1 goes red if it is ever reintroduced as the pin. The harness
  `gamesrv.log` is kept as a **second witness** (165 agree, 1 disagrees — a known
  438 s mispair), because two witnesses to one fact is how a pin stops rotting.
  **§2: the wire field is settled by CONTROL, not inference** — planeA@14 reproduces
  4/30/9 exactly where planeB@16 reads 237 corpus-wide. That check asserts its **row
  count first** (`all([])` is True, and this repo has already shipped a no-collapse
  control that judged zero rows) and separately proves it **discriminates**: the two
  plane words differ in 218 sends, so reproducing the truth is not a coincidence of a
  field that never varies. **§3: the mirrored trigger has not drifted** — the replay
  copies `plane_repair_track` rather than importing it (importing `authsrv.py` opens
  sockets), so it can go stale in silence; §3 re-reads authsrv's own
  `PLANE_REPAIR_HOLD`/`GAP`/`MIN_INTERVAL` and every clause string it reproduces.
  **§4: a stub mesh is not a finding** — `0x287D3` decodes to 27 trapezoids in
  `dat_study`, and folding it in reports 61.3% OFF-MESH about a client that did nothing
  unusual, so stub reports are excluded from the headline denominator and still
  printed per-mesh. Live-fire over the real corpus; absent corpus or archive are
  declared skips, and a skip under the floor is a failure. `--armed` splits every
  headline by whether the repair was actually RUNNING (banner-read, not
  date-inferred) — 3 captures prospective against 131 replayed, and the two
  halves of the arm's case provably disjoint. `--focus <capture>`
  scores ONE session against the corpus and prints an EXPOSURE block — who else
  stood on the same offered planes, and whether they disagreed — because a
  per-session count is uninterpretable without it (FINDINGS §1z-o.7: R7 owns
  every `offered [37]` disagreement in the corpus, and three other sessions
  stood on that ground, one with nearly twice the exposure, disagreeing zero
  times). **§5 pins the one
  invariance the headline rests on**: the five meshes that carry the corpus decode
  identically in `dat_study` and `-probe`, while `0x287D3` really does move
  between them — so the check cannot pass by comparing an archive with itself.
  **A fifth lock was added 2026-08-30 for a defect this file's own
  author shipped**: `label_captures` skipped any capture with zero
  `position_report`s — correct for the census, which scores reports, and WRONG
  for `--echo`, which scores sends. The corpus holds exactly one such capture and
  it is not a curiosity: it carries the **only `0x002A` in the corpus** and that
  send is a TRIP, so the published echo rate read 281/7,542 where the truth is
  282/7,543. The lock asserts every send-only capture is still labelled.
  **§6 was added 2026-08-30 after the FIFTH denominator error in this arc**: a
  capture count left at 30 when the rate sharing its population had been fixed
  to 282/7,543 — a population fix propagates to every figure drawn from it, and
  nothing was checking the others. §6 pins three arithmetic identities
  (on-mesh == AGREE + DISAGREE; scored == on + off; the direction classes
  partitioning DISAGREE) and ten headline figures from §1z-n/§1z-o, each with a
  message naming the section to re-check. **§7 followed the same day**, because
  §6 would have caught none of the EIGHT further defects a denominator audit
  then found — every one lived in a SENTENCE rather than a total: a ratio quoted
  mid-paragraph (map 143's off-mesh rate read 69% for a week; it is 61.3%), a
  histogram still scored on a pre-fix corpus, a claim about what one trace shows
  that was simply false. §7 re-derives each prose figure and asserts the DOCUMENT
  says it — and two of its checks are pure arithmetic ON the prose (the distance
  buckets must sum to DISAGREE; the bimodality buckets to the clean scoreable
  count), which costs nothing and catches a stale population. Writing §7 found a
  ninth: "157 of 174 captures carry exactly zero" folded 40 captures on stub or
  unbound meshes — which CANNOT disagree — into the clean pile. The honest split
  is 134 scoreable, 17 disagreeing, 117 clean. 54 checks, floor 54.
  **2026-08-30, the day after it shipped: both census files found the corpus at
  `<this tree>/vault` — the exact pattern CLAUDE.md forbids** — so from a git
  worktree the census attributed zero reports and the test skipped everything
  (loudly: the floor turned "no corpus" into NO CHECKS RAN, exit 1, which is the
  guard doing its job). Both now resolve the vault via `toolkit/vaultpath.py`
  (`planecensus.py --vault` replaces `--root`), while `FINDINGS.md` and
  `authsrv.py` stay tree-relative, so a worktree session scores the real corpus
  against its OWN tree's prose and trigger mirror.

  `toolkit/clientscan/test_groundz.py` (**GROUNDZ, 2026-09-06: the AgentView HEIGHT read.** MOVECODE sec.1z-cb proved an agent has no z -- its movement record is `(x, y, plane, w)` with `w` a literal zero the client writes on every read -- so the height lives on a different object graph entirely, and `groundz.py` walks there: `view = [[0x00BF96CC] + id*4]`, guarded by the count, a non-null slot, the `0xDB` AvChar type tag, and **the round trip `[view+0x2C] == id`**, which is not a heuristic but ArenaNet's own invariant (its registrar at `0x00801515` writes each object into the slot its `+0x2C` names). What this file can check is NOT that the number is right -- every offset is static disassembly never read from a running client -- but that the walk is the one `studies/renderobj/FINDINGS.md` decoded and that **every way of being wrong is a NAMED REFUSAL rather than a plausible float**: id past the count, an unreadable count, a wild count from a wrong base, a zero count, a null array, a null slot, a short block, the wrong class tag, the round trip failing, a negative id -- ten of them, each with a DISTINCT reason string, because one generic 'failed' would make a wrong base indistinguishable from an absent agent. It also pins that the height comes back with its MEMO (`+0x30`) and the per-agent vertical term (`+0x40`) beside it, since GROUNDZ-F6 established the drawn height is not `+0x8C` alone; that the cache key's plane reads SIGNED (the ctor seeds it to -1 as a never-match sentinel); and that the array constants are stored as RVAs, because the client is ASLR'd. Bare machine, fake memory, no client, no vault. Floor 18 from its first green run. <1 s

  `toolkit/clientscan/test_agenttap.py` (**§6 is MOVECODE-1z-bx (2026-09-05): THE PLANE COLUMN.** `agenttap` now records `plane`/`segplane`/`tplane` — `m_point`'s, `m_segmentPoint`'s (what a `0x0029`/`0x002A` field 3 writes) and `m_targetPoint`'s plane words, signed ints at +0x80/+0x90/+0xA4. The section DERIVES those offsets from `movetap`'s own `A_POINT`/`A_SEGMENT`/`A_TARGET` rather than restating them (so the two cannot drift), pins that all three sit inside the `AGENT_SPAN` block `read_copy` already reads — **zero extra cross-process reads, which is why the gap that blocked ANIMREF §42 for a month cost three lines** — and pins the **signed** decode, because `-1` is the client's own no-plane sentinel and an unsigned read would report 4294967295 and look like a real plane. Floor 18 → 24. The rest is **the AGTRACK FENCE column agenttap
  gained for MOVECODE-1z-an / FINDINGS §1z-an.** `clientControlled` is the dword the
  dispatcher's `0x00606002` tests before the three-gate snap test runs at all — the
  field REALFIX §0.11's two-stage lock account turns on — and §1z-am named reading it
  from this tape as the cheap next step, because `movetap` has read it since §1z-aa
  but NO movetap tape overlaps any lead run and movetap cannot certify under the
  harness anyway. The offsets and the record walk are `movetap.agtrack_fence` CALLED,
  not reimplemented, so `movetap --selftest` still owns them; what this file checks is
  everything agenttap adds on top, each of which is a place a live run would have
  failed silently. `memo_reader` serves one fetch per address per sample AND does not
  outlive the sample (a memo that persisted would stamp a stale fence with a fresh
  timestamp — worse than not reading it), which matters because the AgTrack header is
  per-AgTrack rather than per-agent on a reader already delivering ~9 Hz of the 30 it
  asks for (§1z-ak.7). All four `gate_reach` branches come back through agenttap's own
  call shape with the SYNC block handed over — world 0 being the branch the test at
  `0x006055E0` is actually reached on, and the only thing the choice of copy changes,
  since the record is keyed by agent id. `clientControlled == 0` reads `shut` and never
  a failure value, an unreadable AgTrack reads `unread:` rather than a plausible shut,
  and a block whose own id is not the one we indexed with is refused. `read_copy` now
  returns `(fields, raw block)` — the raw block, because handing `agtrack_fence` our
  decoded dict would mean trusting our own decode twice — and still refuses an id
  mismatch and a short block rather than yielding a partial agent; **that return change
  is what this test caught first, the success path having still returned a bare dict.**
  And §4 is THE NEGATIVE CONTROL DRIVEN BOTH WAYS: `0x00605F10` writes
  `clientControlled` from exactly two callers, both in the ChCliBase local-command
  block, so only the LOCAL PLAYER's agent is client-controlled and the Hatcher's record
  must read `shut` for a whole run — the summary must print both columns quietly when
  it does, and **must go RED when the Hatcher reads `open`**, because that means the
  reader is on the wrong record and the player's column proves nothing. An all-`unread:`
  run must NOT trip that control (unread is a third thing, not a shut fence), and a tape
  written before the column existed — all 17 in the vault — must still summarise rather
  than raise. Bare machine throughout: fake memory, no client, no vault, which is
  possible only because `agtrack_fence` takes a `read(addr, n)` closure. 15 checks,
  floor 15, set from the green run — the floor guard caught a guessed 17 first.
  **The column itself is UNVERIFIED against a live client until one run writes a tape**;
  `--no-fence` reverts it),
  `toolkit/clientscan/test_w0score.py` (**the MOVECODE-1z-t scorer's ENSLAVEMENT
  DETECTOR, MOVECODE-1z-u.5 item c / FINDINGS §1z-x.** `w0score.py`'s number —
  world-0 vs the drawn body — cannot tell "world-0 follows the body" from "the body
  follows world-0": once the client's AgTrack fence is shut every `0x0029` is walked
  as an order and the two copies agree because the body is enslaved, which is what
  made RUN-1zT's p50 0.0 a measurement and not a confirmation. The detector joins the
  tap to the gamesrv capture that produced it and reads, per moving sample, whether
  the ASYNC copy's walk target (+0x9C) equals a SERVER-CHOSEN grant to the unit — a
  `0x0029` that is neither the client's own last click nor within 50 u of its last
  report. Sections 1–4 are bare-machine over synthetic rows: the grant classification
  (at-report / own-click / server-chosen, the point decoded from the row's plaintext
  bytes, NPC grants excluded, the 50 u band from a stop report), the join's
  causality (a grant sent after the sample cannot be the one it follows), the 1.0 u
  band from both sides, own points excepted, parked samples not trials, the onset as
  the first SUSTAINED run of three (two in a row is not one), the three verdicts at
  their bars (FREE at zero, MIXED at 15%, ENSLAVED at 30% and at 29%), zero samples
  and zero grants never crashing, the per-leg table (free leg with its travel and
  median-speed expectation, enslaved leg at 100%, a stampless leg skipped, a leg with
  no moving samples unjudged, a HELD KEY that moved the body under 50 u flagged
  parked, two W legs staying two rows by their start stamp), `find_gamesrv` finding
  nothing for a synthetic epoch, and `score()` joining an explicit `--grants` file or
  saying NOT MEASURED. Section 5 is the vault: the 2026-09-02 zero-lead baseline must
  read FREE with zero server-chosen grants, and RUN-1zT's registered arm ENSLAVED
  from 17.77 s on the tap's clock (18.65 s on the gamesrv clock) with its scorer
  number still p50 0.0 — the contamination is in who follows whom, not in the number.
  Section 6 is the MOVECODE-1z-ac DISCRIMINATOR, and it is the one that keeps this
  file honest about its own false positives: a drawn copy whose OWN target sits
  inside `GRANT_EPS` of a server-chosen grant while world-0 carries the grant reads
  FREE (the co-directional-lead confound, which flagged 44 free samples on RUN-1zAB
  because the 520 u lead was derived from the client's own report chord), the loose
  count still names what was excluded, both copies BIT-IDENTICAL on the grant reads
  ENSLAVED with an onset (what a fence-shut grant actually writes), the threshold
  sits between float identity and the measured 0.53 u confound floor, a known-bad
  arm at twice the threshold is refused because the test is identity and not
  proximity, and a world-0 with no leg armed enslaves nothing.
  **Section 7 (MOVECODE-1z-bh, 2026-09-05; review §1.1) is the MOVING-ONLY
  LINE.** `w0score`'s headline p50 is ALL-SAMPLE, and on the shipped lead-OFF
  default the stop echo parks world-0 on the body at every stop, so the parked
  majority drags the median to ~0 while the copy runs a full report chord behind
  whenever the body walks — the registered §1z-t.8 verdict printed CONFIRMED over
  exactly such a tape. The section builds that tape (20 walking samples 500 u
  behind, 30 parked samples on the body) and asserts the all-sample p50 under the
  CONFIRM bar, the moving-only p50 over 400 u with n = 20, and the line PRINTED
  beside `<-- THE NUMBER` rather than instead of it; its control is a walk-only
  tape where the two statistics must AGREE, so a green cell is the parked
  majority doing the work and not two differently-computed numbers. The verdict's
  registered semantics are unchanged — the moving-only reading is printed beside
  it, labelled "NOT the registered statistic".
  Floor 47, from the BARE-MACHINE green run (50 with the vault; section 5's three
  real controls are the difference and declare a skip). **A skip does not lower a
  floor**, so the old 44 was unreachable without a vault after §1z-ac's section 6
  landed — corrected here in the same change. ~5 s with the vault),

  `toolkit/clientscan/test_leadmargin.py` (**the keyboard lead's LENGTH argument,
  MOVECODE-1z-ab / FINDINGS §1z-ab.** `leadmargin.py` holds the three extractors the
  argument rests on, and this file drives each over synthetic rows in a temp dir with no
  vault: the cruise-chord extractor's rules (same heading within 1.15°, same non-zero
  movementType, a `0x0047` breaks the pair, the 1 s gap floor excludes the heartbeat, the
  320 u/s bar excludes teleports, a malformed row is skipped and the pair around it
  survives, an idle pair is nothing), the census (the in-band count and 1 u excess
  histogram over the 512 u trigger, the ceiling, the tail split into LATE REPORTS under
  1.15 triggers and SILENT WALKS at or over it, an empty corpus a census not a crash);
  the per-leg reading on a tap (legs from the sync copy's own target fields, the live
  position by the client's own clamp-then-dead-reckon rule so a walking leg's distance
  to go is read from the live point and not the +0x78 origin, a matured leg's park from
  the clamp, live-vs-live separation, the speed families off the velocity fields, a
  100 u stub dropped, `until` cutting a contaminated tail); and the BOUNDS against
  `authsrv`'s own constants — the module's decoded constants equal the server's (run
  speed, gate 1, the reprieve radius), the hold window is floor + one tick, the shipped
  520 u lead cannot mature inside it and outlasts the trigger, the hold's cross-family
  residual is under gate 1 while its SAME-FAMILY residual is pinned as NOT under it
  (316.8 vs 299.33 — §1z-ab's recorded residual; a floor or tick that silently changed
  either goes red here), the order-walk cost is the lead itself so 766 costs 246 u more,
  a measured ceiling enters as its own inequality, two KNOWN-BAD ARMS (400 u fails the
  trigger, 100 u matures inside the hold), and the constant is 520. Section 4, vault-
  gated with a loud skip: `leadmargin --check` reproduces the corpus figures as floors
  and signatures — 1,126 in-band chords, ceiling in [517, 520), six hitches under 600 u,
  28 silent walks, and on the two lead-ON taps no leg parked longer than one sample with
  RUN-1zT's three cruise legs one of them at its point when the re-aim landed. Floor 24
  from the bare-machine run; 25 with the vault.)

  `toolkit/clientscan/movehook/test_movehook.py` (**MOVECODE-B2's hook DLL, and
  the first test any hook in this repo has ever had.** `trnhook/` has none, and
  `srclint` therefore imposed nothing on it — which was *silence, not a ruling*,
  until the owner made it one: `PLAN.md` §7 Q12(b), 2026-08-26. A hook is an
  instrument whose whole output is a ledger and whose interesting answer is often
  a small number, which is the worst shape for a tool to break quietly in: **"the
  hook was dead" and "the client never did it" produce the same zero.** §7 is the
  section the ruling bought. It injects the real DLL into a real 32-bit
  `SysWOW64\cmd.exe` and reads the sidecar back, and it works *because* the four
  hook RVAs are ~2 MB into an image that small — **every site fails to arm**, and
  that is the property worth testing: the DLL must survive unresolvable sites,
  leave its host running, and report `hits 0` honestly. Control A (an `int3` in a
  buffer the DLL allocated) must still fire, because it touches no host byte —
  a control on the control. Control B came back COULD NOT ARM, which is the
  three-valued path working rather than a failure: an idle `cmd.exe` has no
  thread executing in `.text` to sample. **Two defects this section found before
  any client run.** The host was spawned with `stdin=DEVNULL`, so `cmd /k` read
  EOF and exited within half a second; the injector then failed on a module
  snapshot with `WinError 299`, which reads exactly like the known
  64-bit-enumerating-a-WOW64-target bug and sent the first diagnosis at
  `TH32CS_SNAPMODULE32`. MEASURED: DEVNULL → host dead at t=0.50s and never
  resolves; a held-open pipe → `kernel32` resolves at t=0.25s. **The error was
  about the corpse.** And the floor was first written as 16 by adding up what the
  sections looked like they held; the real process-free core is **18**, so two
  checks could have stopped running with the suite still green — the floor is now
  counted per section off the banner (§1 6, §2 5, §3 4, §4 11, §5 3, §6 2, §7 5;
  36 whole). §5 is the file's negative control and it is the one that can go red
  in the useful direction: a capture whose sidecar says control A DID NOT FIRE
  must be **refused**, not scored, and the test asserts no rate is printed after
  the refusal. §3 is what makes `PLAN.md` §7 Q12(a) worth anything — it breaks a
  `hook_site` row four ways (no `build`, no `extractor`, an extractor that is not
  in the repo, and a well-formed control that must LOAD) and requires
  `content.py` to refuse three of them; if it did not, putting the addresses in
  TOML bought nothing over `#define`s. §1 asserts the checked-in `sites.h` is
  byte-identical to what `gensites.py` emits, because a hand-edited generated
  header is exactly the two-homes split the ruling refuses and is otherwise
  invisible. §2 requires every site's first byte to be **its own SHAPE's byte** in
  the pinned 38797 image — `0x55` for the `push ebp` entries, since 2026-08-29
  `0xC3` for the four MapFindPath `ret` sites, and since ANIMREF-RE (2026-09-01)
  `0x57` for the `resume_arm` site (`push edi`, a third one-byte no-operand
  shape with the same safety the entry rule had) — because that byte IS the
  instruction the handler will re-emulate. Note what it deliberately is NOT: a
  check that accepts "any of the three" anywhere would let a ret's emulation be
  armed on an entry byte, so the pairing is per row and is checked as a pair — a
  tighter gate than the single global constant it replaced, since an entry that
  decayed into something else is still caught. §9's 0x55-everywhere control
  counts refusals over EVERY non-`0x55` shape (the four rets and `resume_arm`),
  derived from the rows rather than a literal, so a new shape reddens the count
  instead of sliding under it. The 2026-08-28 sites plus the ANIMREF-RE ones
  (`movecmd`, `inputeval`, `movecache`, `movedispatch`, `resume_arm`,
  `resume_fire`, `heldbit`) bring the full run to 302 checks; the bare-machine
  floor stays 169. **§8 pins a bug that would
  otherwise have been invisible until a live run produced a ten-minute capture
  nobody asked for**: `GetEnvironmentVariableA` inside an injected DLL reads the
  *client's* environment, inherited from whatever launched `Gw.exe`, **not the
  injector's** — so `attach.py` exporting a variable would change nothing and the
  DLL would quietly use its defaults. The config therefore lives in a
  `movehook.cfg` beside the DLL, and §8 sets the file and the environment to
  DIFFERENT output directories and a 1500 ms against a 600000 ms run, so which one
  the DLL actually honoured is visible in where the sidecar landed and in whether
  the run finished. **§9 is the most important guard in the directory and it is
  the one `gensites.py` structurally cannot provide.** `session.py --exe` defaults
  to the NEWEST build under `vault/run/` — the `sorted()[-1]` trap this repo has hit
  three times in three files — while every movehook address is 38797. Arming a
  38797 RVA in a 38833 image is not a wrong number, it is a **crash**: the `0xCC`
  lands in the middle of some unrelated instruction and the client dies with our
  patch in it. `gensites.py --check` reads the PINNED FILE, so it answers OK no
  matter which client is actually running — it is checking the wrong artifact. So
  `attach.py` re-verifies the same property against the **live process** and
  refuses. §9 exercises BOTH directions with `keytap` monkeypatched, because a
  guard that only ever refuses is indistinguishable from a broken one: 0x55
  everywhere must ACCEPT, one wrong byte must refuse and NAME the byte it found,
  and an unreadable site must refuse rather than pass by default. A live positive
  control was tried first and only reached the "no Gw.exe module" path, which
  proves the weaker half. **§10 is MOVECODE-B3's half**, and it runs against the
  REAL Ascalon mesh rather than a stub, both ways: a connected pair must score
  `BOTH-OK` and a goal a million units out must score `OFF-MESH` and NOT quietly
  read as fine — because `OURS-FAILED` and `OFF-MESH` are claims that *our* decode
  is wrong, and a harness that cannot tell them from `BOTH-OK` would launder our
  own bugs into a clean bill of health. It also round-trips a synthetic v3 capture
  through `pathdiff.queries()` and requires the DEREFERENCED coordinates to
  survive: the client passes `MapFindPath`'s from/to **by reference**, so a record
  storing only the argument dwords holds addresses and nothing replayable — which
  is what writing `pathdiff.py` discovered and what took the record to v3. §4 pins
  that **a v1 capture still parses**, because run 1 is v1 and is the arc's only
  live evidence; versioning that orphaned it would have been worse than not
  versioning. **§11 is the section that exists because the length check was not
  enough, and it caught a defect that had already shipped two wrong runs.**
  `readhook.py` described v3 as *scalars + point/segment/target/pt_a/pt_b* with
  `have_pts` appended to the scalars; `movehook.c` declares `have_pts` AFTER
  `target[4]`. Both spell 38 dwords, so `reclen` matched and the guard whose own
  message warns about "a record whose fields would silently shift" COULD NOT FIRE —
  every point block read one dword late, `have_pts` came back as `m_point.x`, and
  `pathdiff` reported "no coordinates" on a capture that had them. A length check
  cannot catch a reorder, so §11 PARSES `rec_t` out of movehook.c and compares name
  and width IN ORDER. Planting the exact historical reorder makes it go red, which
  was verified rather than assumed. The fixture builder was rebuilt the same way:
  `_synth` now walks `readhook._LAYOUTS[ver]` instead of encoding the field order a
  second time, because a fixture that re-states the layout can agree with a wrong
  reader and prove nothing. **§12 is the world-copy census, and it exists because
  the reader had no concept of the structure the client actually has.**
  `WORLD_CREATE_AGENT` builds each agent in BOTH worlds — the handler runs its body
  twice with the array base advanced `0x64`, and `AgAgent.cpp:312` names them
  `m_world` 0 and 1 — so **one agent id names two objects**. Every per-agent
  trajectory this directory has ever computed filtered on `id == 1` and treated the
  result as one body; in the run 5 capture the two copies sit **940 u apart**, so
  such a walk crosses between them and reports the crossing as a displacement
  *inside a single 15 ms `GetTickCount` tick*. That is how FINDINGS §1h.2 scored the
  warp rate. `id` cannot separate them and `ecx` — the object's address — can, so
  the census groups on the address, names the sync copy from `reseed`'s source
  argument rather than assuming it, and RAISES when an id is ambiguous. Both
  directions are exercised, because a warning that cannot stay quiet carries no
  information: a capture with one object per id must NOT warn. §12 also carries the
  **non-agent guard**, and it is deliberately built as a comparison between two
  measurements rather than against a literal — an agent's declared leg
  `[ptime, stop]` cannot outlast the capture that observed it. `snaptest`'s `ecx`
  was marked `thiscall` because `0x006055FB` saves `ecx` to a local, and it produced
  70 records with agent ids 574588536 / 459313176 and a p50 separation of 7,197 u
  that read as a catastrophic desync; that object declares a 28-hour leg inside a
  192 s run and is now called out by name. Writing this section also caught its own
  fixture: the first draft spaced synthetic ticks 10 ms apart while giving legs
  1000 ms, so an *honest* agent tripped the guard — the fixture was widened rather
  than the guard loosened, which is the direction that matters. **§13 is the DISPLACEMENT
  count, and it exists because a reseed that FIRES is not a warp** — run 5 had 14
  reseeds and 2 displacements. Counting reseeds alone would score a candidate that
  fires less but warps more as an improvement, which is exactly how four of the five
  dead candidates in `authsrv.py`'s movement graveyard flattered themselves. The
  signature needs no threshold: a WALK advances both `m_point` and the `+0x58` stamp
  saying when `m_point` was valid, while a displacement moves the point with the stamp
  STANDING STILL. All four directions are exercised — a walk must NOT count, a frozen
  stamp MUST, it must be attributed to the reseed rather than the teleport that
  preceded it (run 5: 10 displacements, only 2 after a reseed), and sub-unit float
  noise must not count, because two reads of a parked agent differ in the low bits.
  The distance is printed beside the count, since a bare count cannot tell a 5 u nudge
  from a 691 u warp. This is the number `MOVECODE-K1`'s registered prediction
  (FINDINGS §1k.3) is REFUTED by. **§14 is the 2026-08-28 sites and the v6 fields,
  and its first half exists because a gate nothing has ever tripped is a gate nobody
  has tested.** §2 checks every row's first byte *is* `0x55`; that is the positive
  side and it cannot show the refusal works. FINDINGS §1s.9 asked for four hook sites
  and named five addresses, and **four of the five are not function entries** —
  `0x00606009` is a `je`, `0x00605634` a `cmp`, `0x00605683` a `pop esi`, and
  `0x005FCAA0` the ResyncAllAsync *thunk*, a `call`. So §14 clones a real row onto
  each of those four real addresses and requires a refusal — **twice each**, because
  the second is the one that encodes the ruling: first as anyone would naively write
  it (address changed, `first_byte` still `0x55`, caught by the byte-mismatch guard),
  and then "fixed" so `first_byte` matches the byte actually there, which is what a
  session does after reading the first refusal. `PLAN.md` §7 Q12(d) is a constraint on
  the HANDLER, not a typo in the row — matching the row to the binary does not make a
  `je` emulable as a `push ebp`. A control runs first: the row all four are cloned
  from must still be ACCEPTED at its own address, or every refusal is about the
  cloning. The second half round-trips the v6 fields, and the check that carries it is
  that **an UNREAD fence is distinguishable from a fence read as zero** — `have_fence`
  exists so "could not read it" and "it was shut" are not one value, which is the
  §1s.8-item-1 failure class in miniature: a state that was never observed scoring as
  a state. **And the check the R2 run itself bought:** v6 shipped with all six fields
  written correctly and NO report section, so the fence, the facing and the gate-3
  filter sat in the capture while the readout said nothing and the run's five
  registered predictions had to be scored out of a scratchpad script. Round-tripping a
  field cannot catch that — only asking the REPORT can — so §14 requires all four v6
  sections to appear on a v6 capture, with the control that a **v5** capture prints
  none of them, since a section built from absent fields would read as a measurement
  of zero rather than of nothing. **And the row R2's own result asked for:**
  `setposition` (`0x00602B20`), pinned as the CALLEE — §1t.8 named two call sites,
  `0x00604A50` and `0x00606394`, and neither can be hooked because both are
  `e8 call`, so the row hooks what they call and reads the caller off the return
  address. §14 pins the two things that would break that silently: `deref_arg_a`
  no longer dereferencing arg1 (the installed point stops being captured and every
  warp measurement reverts to inferring it from the next record), and `why_hooked`
  losing the two addresses that are the row's whole justification. That second
  check went red on its first draft because it read `provenance.verified`, which
  `gensites.rows()` does not return — the check catching the test's own wrong
  operand rather than the row's. **And the off-by-five that caught the orchestrator on
  R3's very first readout:** the record stores a RETURN address, every one of
  SetPosition's seven callers is a 5-byte `call rel32`, and a caller table keyed on the
  CALL addresses — which is how `--xrefs` prints them and how both `FINDINGS.md` and
  `content/movecode.toml` cite them — reports every known caller as UNKNOWN. §14 asserts
  the table is keyed on call+5 and that no call address appears as a key; planting the
  exact regression reddens both checks. **And the tick, which forced a new mechanism:**
  `0x00600140` runs per agent per frame, and movehook's worker *ends the run* when the ring
  fills — so an unstrided per-frame site would not truncate the tail, it would cut the
  capture short and starve every other site. `stride` stores 1 hit in N while `g_hits[]`
  still counts every one, so the denominator stays exact. §14 pins the arithmetic
  (occurrence 1 is always stored, so a site that fired once still appears; `nth % stride`
  would drop it) against movehook.c's own expression, and — the guard that matters more
  than the row — requires every site whose RECORDS are counted to be unstrided, since a
  stride there would turn the displacement census, the reseed split, P1a and the gate-3
  filter into silent 1-in-N samples while `hits` stayed whole. Planting `stride = 8` on
  `reseed` reddens that check *and* the generated-header check independently. **§9 also now owns
  the stale-DLL guard**, which refused a byte-identical DLL in the middle of a live run —
  twice, because it compared *mtimes* on a generated, git-managed header that
  `gensites.py` rewrote unconditionally and git then normalised on commit. It is decided
  by a build-stamp sha256 now, with mtime as the fallback for a DLL predating stamping,
  and all four arms are exercised: a matching stamp passes, it **still** passes when
  sites.h is newer but byte-identical (the false alarm), an actually-edited header is
  refused, and with no stamp it falls back to mtime and says so. **§15 exists because the
  client CRASHED:** the stride was written as `if (strided out) continue;` directly above
  the `push ebp` emulation whose own comment reads *"this must happen on every hit — a
  skipped prologue is a corrupted frame, not a missing sample"*. `continue` leaves the
  for-loop, so EIP never advanced past the `0xCC`; 63 of every 64 tick hits took that path
  and the client died with `c0000005` within seconds of arming. **Nothing in the suite
  could have caught it** — §7 injects into a throwaway `cmd.exe` where every site
  deliberately fails to arm, so the handler's hot path is never executed by a test. The
  property is structural and is now checked structurally: no `continue`, `break` or stray
  `return` between the address match and the emulation, with a control that plants the
  exact crashing statement and confirms detection. **§16 IS DURABILITY, AND IT
  EXISTS BECAUSE AN 8-MINUTE CAPTURE WAS LOST.** MOVECODE R5, 2026-08-28: the
  operator armed, played, ran `--stop`, and got no `movehook.bin`, no
  `movehook.txt`, and no output directory at all — the run had to be scored from
  the server log instead. Three defects, all in the instrument: the DLL wrote
  **exactly once**, past the end of its poll loop, so any ending that loop did not
  reach discarded every record; **nothing was written when the process exited**;
  and a failed write was **silent**, `fopen`'s NULL dropped on the floor, so an
  unwritable path was indistinguishable from a run that captured nothing. What
  makes this a testing lesson and not just a bug: **§7 asserted the `.txt` sidecar
  and never once asked whether the CAPTURE existed** — the summary, not the data —
  so no check in this file could have caught it. §7 now requires the `.bin`, its
  `MVHK` header, that `readhook.py` can PARSE what the DLL just wrote (the writer
  was rewritten from stdio to Win32 under this change, and "the bytes still mean
  what the reader thinks" is exactly what that could break), and that no `.part`
  temp survives — the write is atomic, temp-then-rename, so a snapshot interrupted
  mid-flight cannot replace a good capture with a truncated one. §16 itself checks
  the poll loop snapshots on a bounded timer, that `DllMain` writes on
  `DLL_PROCESS_DETACH` and stands down once the worker's own final write has
  happened, that the writer is Win32 rather than CRT stdio (it is called at process
  shutdown, where stdio can deadlock under the loader lock) with a control that no
  stdio slipped back in, that failures reach `g_werr` and a `movehook.status` file
  **beside the DLL** — the one place still writable when the output path is the
  broken thing — and that `attach.py` proves the path writable BEFORE injecting and
  that `--stop` now WAITS for the artifact and reports a missing one instead of
  promising it ("the DLL polls at 100 ms; it will disarm and write within a second"
  was printed on R5 and was false). **The exit path is verified behaviourally, not
  just structurally**: a real 32-bit `cmd.exe` is injected with a long timer, a
  CONTROL confirms nothing is on disk mid-run so the file cannot be attributed to
  the normal ending, then its stdin is closed for a GRACEFUL exit — `TerminateProcess`
  would not run `DllMain` and a test built on `kill()` would prove nothing — and the
  capture must appear. **§16 RUNS ONE HOST PER MECHANISM, and the reason is a red it
  produced:** its first version tested the periodic snapshot and the exit write through
  the SAME host and told them apart by **mtime**, which cannot work — the two writes
  landed 86 ms apart, so the "before" reading was already the exit write's and the check
  compared a write against itself. Neither mechanism was broken; standalone repros of
  both passed. **Two mechanisms racing through one artifact cannot be attributed by
  looking at the artifact.** So (f) proves the graceful-exit path, and (g) proves the
  snapshot in a SECOND host: wait past `FLUSH_MS` (read out of the C source, never
  restated in the test), require the file **with the host still alive**, then
  `TerminateProcess` it — no `DllMain` runs at all — and require what survived to be a
  capture `readhook.py` parses. That second host is the case the first cannot reach: a
  hard kill is the harness's own fallback when WM_CLOSE times out, so without a mid-run
  flush the fix would only have covered a graceful close. **Three checks went red against
  the fix and all three were the test working:** one read `WriteFile` inside `write_bin`
  when that call lives in its one-line `put` helper (a wrong OPERAND, the second this arc
  has paid for); one still looked for `snapshot(` after the detach path was inlined; and
  the mtime race above, which on the way turned up a genuine defect — `outdir()` reads
  the cfg through `fopen` on every call and the DETACH path called it, at the one moment
  the CRT cannot be trusted, so the path is now resolved once at arm time and the
  shutdown path builds strings with kernel32 rather than `snprintf`.
  **§15b and §17 are the MapFindPath RETURN tap, 2026-08-29 (HANDOFF-PLANE §4.2).**
  §15b exists because §15 structurally cannot catch the bug the second emulation
  shape introduces: the emulation is now a branch on `SITES[i].shape`, and the way
  to break it is not a `continue` but an arm that falls through **without assigning
  `c->Eip`** — a missing `else`, or a new shape with no arm — which leaves EIP on
  the `0xCC` and re-traps forever, and at `0x0070A0D4` the following eleven bytes
  are the compiler's own `int3` padding so it is not even loud. `_loop_escapes`
  scans for continue/break/return and a missing else is none of those, so §15b
  counts the arms against the assignments and requires them equal — with §15's own
  control discipline: delete an assignment and the checker must go red. §17 holds
  the four ret rows to what the disassembly proved and the generator to its
  refusals. The one that would have silently corrupted every capture: **a ret row
  must NOT inherit the entry row's `deref_arg_b = 2`**, because MapFindPath reuses
  its caller's arg2 slot as FPU scratch (`fstp [ebp+0xc]`, nine times, the first
  three before any branch), so at every ret that slot holds a FLOAT — and
  `readable()` can ACCEPT it, since 10000.0f is `0x461C4000`, a plausible committed
  address in a 32-bit client. Sixteen bytes of unrelated memory would have been
  stored as "the destination" and scored OFF-MESH, reading exactly like the decode
  gap the tool exists to find. That is a REFUSAL in `gensites.py` rather than a
  value in a row, and §17 proves all five refusals fire, including one on a site
  (`chcli_dir`) that trips no structural rule so the BYTE half is exercised rather
  than short-circuited. §17 also pins v7 as APPENDED (`v7[:len(v6)] == v6`) and
  round-trips a synthetic capture through the **(tid, esp) pairing**, whose key is
  also its own audit: all four exits are `8B E5 5D C3`, so a pair whose two `esp`
  values disagree REFUTES the premise the tap rests on and must be counted and
  printed rather than paired anyway. **§17e is the split that was the point.** The
  three-valued scorer called "we found no route" `OURS-FAILED` *without knowing
  whether the client found one*, so every query neither side could answer inflated
  our own decode-gap number by an unknown amount — the MOVECODE-Q2 headline. §17e
  scores all five verdicts against a stub mesh (process-free: the assertion is
  about verdict LOGIC, not geometry) and carries the control that makes it mean
  something — the same `BOTH-FAILED` query, scored by the OLD path, must come out
  `OURS-FAILED`, or the section is asserting a distinction that never existed.
  `UNREADABLE` is checked separately from `pathCount == 0` for the reason
  `have_fence` exists: pathCount 0 IS §4.2's registered lock prediction, so merging
  "could not read it" into it would manufacture evidence for the thing being tested.
  **§17f and §18 are the two defects R7 found in our own scorers, each pinned
  against a known-bad arm.** §17f: the shape metric was a TAUTOLOGY — it compared
  our route's last point to the client's last waypoint, and the callee overwrites
  that slot with the requested destination verbatim while `route()` ends at the goal
  by construction, so both operands were the destination. The gap read exactly 0.0
  on 129 of 131 live comparisons, DIFFER never fired once in 214 queries, and a
  deliberate 800 u perpendicular detour scored PERFECT AGREEMENT. §17f asserts the
  replacement (symmetric Hausdorff) ranks that same detour badly, and demonstrates
  the disqualified last-point form scoring both identically right beside it.
  **§18 is the map identifier, and it is the sharper lesson**: `--map auto` scored
  the fraction of endpoints landing on each mesh — a score with an AREA TERM, so a
  bigger mesh swallows any point cloud. On the r7 capture Sparkfly Swamp scored
  99.3% against map 280's own 81.8% and WON; believed, it reports OFF-MESH 3 instead
  of 63, making our decode look **20× better** in exactly the signal the tool exists
  to produce. The old guard beside it fired only BELOW 50% coverage — built for the
  direction where a wrong map looks BAD — and **a guard that only fires when the
  answer already looks wrong is not a guard.** The fix adds the client's own PLANE
  word, conditioned on the points that landed so size cancels, restricted to
  non-zero planes because plane 0 agrees by coincidence on any mesh. §18's known-bad
  arm is a REAL one rather than a constructed one — the mesh that actually beat the
  true map — and it asserts the REFUSAL THRESHOLDS ARE UNCHANGED, so a future
  loosening cannot be smuggled in as "making the fix pass". It carries the control
  that a correct map produces no warning, because a guard that fires on the right
  answer too is noise. Archive-dependent, so the floor does not move for it.
  **§19 is the motion window, where ONE EXPRESSION carried THREE defects.** The
  world census computed `max(ptime) - min(ptime)` over every record. (1) An
  UNSET stamp is not a timestamp: exactly two records per object -- the run's
  first `setter` and `bake` -- carry `ptime == 0`, dragging `min` to zero and
  inflating the denominator by the whole pre-capture uptime; r7 printed "in
  motion 61.8%" where the truth is 87.8%, a **27-point error from 2 records in
  1,785**, present in EVERY v4+ capture in the corpus. The existing
  impossible-leg guard cannot catch it because those records carry `stop == 0`
  too, so `stop > ptime` is false -- **that guard tests the LEG and this defect
  is in the STAMP**, which is why a new check was needed rather than a wider
  threshold. (2) `stop` is a PREDICTED FUTURE arrival, so de-zeroing alone still
  produced percentages OVER 100 (107.9% on run3-isle); legs are now clipped into
  the observed window rather than the window stretched to fit them. (3) It
  raised KeyError on v1-v3, which have no `ptime` field at all -- so
  `readhook.py --bin` CRASHED on run 1, the arc's only v1 capture, while §4 pins
  "a v1 capture still parses": true of the PARSE and never of the REPORT. Two
  separate sites had to be fixed and **the second was found by this test rather
  than by reading**, which is the argument for writing it. The control is the
  one that makes the section mean anything -- the OLD expression, applied to the
  same fixture, must still produce the inflated 110 s denominator -- and the
  exclusion is COUNTED AND PRINTED in the report, because "we ignored two
  records" and "there were none" are different facts and the first is the one
  that explains a number. Process-free (synthetic captures only), so the floor
  moves with it.
  **§17 also carries the v8 widening (2026-08-29, FINDINGS §1z-m).**
  `RET_MAX_POINTS` went 4 → 9 -- the larger of the two callers' own maxCount,
  confirmed live at 214/214 -- so `out_path` can no longer truncate for either
  known caller. It landed as a NEW capture version rather than a wider v7, and
  that is the part worth copying: r7 is a v7 file and the arc's only capture
  carrying the client's own answers, so redefining v7 in place would have made
  `reclen` disagree and ORPHANED it -- the same failure §4 pins with "a v1
  capture still parses". §17 asserts BOTH layouts still exist (4 points and 9),
  that the C and the reader agree on version 8, and that `ret_capacity()` reads
  a v7 record as 4 and a v8 record as 9 -- because two readers had been quoting
  the module constant as THIS record's capacity, which becomes a lie the moment
  the writer moves. The C deliberately keeps the LITERAL `out_path[36]` rather
  than `[RET_MAX_POINTS * 4]`: §11 parses `rec_t` with a digits-only pattern,
  and an expression would drop the widest field in the record silently out of
  the one check that can catch reader/writer drift.
  169 floor,
  285 on a
  machine with the client, a compiler, an archive and a 32-bit `cmd.exe`; each other
  section declares a skip),
  `toolkit/clientscan/test_commandertrap.py` (the hardware-breakpoint trap, and
  the section that matters CAUGHT A DEAD TOOL BEFORE IT PUBLISHED A FINDING.
  `commandertrap.py` answers "does instruction X ever execute", and the
  interesting answer is NO — the worst possible shape for a silent break,
  because a trap that arms nothing produces exactly the same output as the
  result. So §3 spawns a real 32-bit `cmd.exe` under the debugger, arms an
  execute breakpoint on the entry point the OS itself supplies, and REQUIRES
  the hit. First run: no hit. The debug registers were armed correctly (read
  back: `Dr0` = the entry point, `Dr7` = 1) and the processor did trap — but a
  64-bit debugger receives a WOW64 target's exceptions as
  `STATUS_WX86_SINGLE_STEP` (`0x4000001E`) and `STATUS_WX86_BREAKPOINT`
  (`0x4000001F`), not `0x80000004`/`0x80000003`, so every hit was being handed
  back to the target as somebody else's exception. Without this section that
  would have run against the client and reported the arc's headline — "the
  commander event is never raised" — as a measurement. **And it caught a SECOND
  break, from its own first version's blind spot.** §3 originally stopped at the
  first hit, which proves a breakpoint FIRES and says nothing about whether the
  target RESUMES past it — so the live run trapped one instruction 32 times in
  4ms, identical `ESP` each time, until the runaway guard disarmed the slot, and
  reported it as "that site executed 32 times". A hardware execute breakpoint is
  a *fault*: `EFLAGS.RF` does not survive the trip out through
  `ContinueDebugEvent`, so the debugger must set it explicitly on the way back
  in. §3 now runs to process exit and requires **exactly one** hit on an entry
  point that runs once, plus a clean exit — firing and resuming are separate
  claims and only the first was being made. §1 pins the DR7
  encoding, including that bits 16+ are ZERO: a nonzero R/W field is a *data*
  breakpoint wearing the same address, which does not error and never fires on
  execution. §2 checks EVERY site's bytes against the 38833 image ON DISK — 19
  of them as of 2026-08-17 — so a typo'd address is caught with no client at
  all. That count grows with the arc (`raise114`, `lookup114`, `gmvEvent`,
  `gmvEventAny`, `gmvSub114` came from the PvP-UI arc), and §2 iterates `SITES`
  rather than a hand-kept list precisely so a new site cannot be added without
  being checked. §4 proves
  `verify_sites` accepts bytes that match and REFUSES bytes that do not — the
  cross-build guard, and this arc read a 38797 address in a 38833 binary once
  already. §5 breaks the verdict's control gate both ways. §6 pins the capture
  decoders, including the filter's PASSES/REJECTS string, which is the run's
  headline, and that an unreadable entry decodes to `None` rather than to a row
  of zeros that would read as a real measurement. §3b covers DEFERRED arming,
  the mechanism that makes a hot site measurable — `lookup` sits inside the
  raise every UI event passes through, so it is armed only when its trigger
  fires and taken down after one hit. The hazard is specific: a deferred site
  that never arms is SILENT, and silence is exactly what its finding ("no
  subscriber") looks like. Checked by reading the debug registers back out of
  the live thread — the deferred address must land in `DR1` **and** its enable
  bit must appear in `DR7`, since an address sitting in `DR1` with no `L1` is
  silence again. The obvious behavioural version cannot work and the test says
  why: a hardware execute breakpoint fires on an instruction's FIRST byte, so a
  dependent at `entry+1` is mid-instruction and would be silent for reasons
  unrelated to deferral. §§2-4 need the vault and a 32-bit Windows and SKIP with
  their reason. **§7 is the COVERAGE half, added 2026-08-23 and it is the one
  that makes every other hit count mean something**: `armed_now()` existed
  from the start and was called only from this test, so no RUN had ever
  verified that its debug registers were actually live on every thread --
  and `arm_failures == 0` counts only the threads the trap TRIED.
  `snapshot_coverage()` reads DR0-DR3/DR7 back per thread, names any
  thread missing a site, reports an unreadable context as unreadable
  rather than as armed, and `_report` prints **NOT SAMPLED -- a zero hit
  count from this run is not evidence of absence** when no snapshot
  exists. The checks run against a fake trap with no process at all.
  §7 grew TWO more on 2026-08-23, and they close a hole in the coverage
  half itself: coverage was sampled only at ATTACH, so a run that started
  covered and lost its registers at hit one printed a healthy `10 of 10`
  all the way through -- which is exactly what the resume path did to the
  row watch for three runs. `pump()` now takes a SECOND sample at the end,
  while the process is still alive; the two are kept in separate fields so
  one cannot be printed twice, and a shortfall makes `_report` say
  **COVERAGE WAS LOST DURING THE RUN** above the hit counts. Both are
  broken on purpose against the fake trap.
  **§8 is the DATA WATCHPOINT** -- DR R/W = 01 instead of 00, which §1's own
  check calls out as the silent failure mode of a wrong R/W field, now made
  the deliberate case. It pins the encoding per SLOT (a write watch in slot
  1 must leave slot 0's fields at 00), requires an unknown kind or a
  3-byte length to be refused BY NAME rather than encoded as something
  else, and pins `arm_watch`'s two refusals -- a slot the processor does
  not have, and **an unaligned address**, which is the important one: a
  misaligned DR does not error, it watches the wrong bytes and reports
  silence, the worst possible failure for an instrument whose job is to
  catch a rare write. **§9 exists because a "fix" was audited and turned out
  not to be one, and it is the shape of check that would have caught it.**
  On 2026-08-23 `adopt_existing_threads` was added against the reading
  "after attaching to a running client, `self.threads` held ONE thread" --
  sampled inside the CREATE_PROCESS handler, the FIRST debug event after
  attach, where one thread is what you see whether or not the OS goes on to
  deliver a synthetic CREATE_THREAD per pre-existing thread. It does deliver
  them. §9 starts a 32-bit `cmd.exe` normally (the client's own bitness --
  `_arm` writes a `WOW64_CONTEXT`, so a 64-bit target would answer the
  enumeration half and silently fail the arming half), waits for it to reach
  several threads, requires **>= 3 as a positive control** (a single-threaded
  target agrees with both hypotheses and makes the section vacuous), then
  attaches **with adoption disabled** and requires the debug loop to reach
  all of them unaided, every one verified holding the armed address, with no
  arming failures and coverage intact at the END of the run. The last check
  is the pointed one: on the same target with adoption ON it still reports
  `(5, 4) found, newly armed` -- so that second number is a count of threads
  the loop had not ANNOUNCED yet, never a count of unwatched ones, and the
  misread is reproduced on demand rather than argued about. Full audit:
  `studies/heroes/FINDINGS.md` §39. Floor 31 = the mandatory core
  (§1+§5+§6+§7+§8); §§2-4 and §9 need the vault and a 32-bit Windows and SKIP
  with their reason; a whole green run is 71, ~20s. **The core is MEASURED as of
  2026-08-30, not just arithmetic**: `RURIK_VAULT` at an empty directory gives
  **50 checks, 1 declared skip (§2), rc=0** on a machine that still has its
  32-bit `cmd.exe`, and with `WOW64_CMD` also pointed at a path that does not
  exist, **31 checks, 5 declared skips (§2, §3, §3b, §4, §9), rc=0** — exactly
  the floor, zero slack. Neither run reached a verdict before that day:
  `pinned.find()` raises `SystemExit`, `except Exception` at §2 did not catch it,
  so §1 printed its five PASSes and the file died with rc=1 and no banner),
  `toolkit/clientscan/test_compositetrap.py` (**the composite pipeline's runtime
  instrument, checked without a client** — `compositetrap.py` is the probe for
  playercomposite §4.12 ("nothing here was checked against a running client"),
  and this is everything about it that can go red at a desk. §1 checks both
  sites' recorded bytes against the pinned 38797 image (an address typo is
  otherwise invisible until a run arms on the wrong instruction — and
  `verify_sites` would still pass, since it compares the same wrong bytes with
  themselves). §2 requires the sites to DECODE as claimed: the record
  resolver's own `lea eax,[esi+esi*2]; shl eax,4` gives the stride 48 and its
  operand gives the base global the capture reads, its `cmp` gives the count
  global P5 bounds against, and the base lookup's `prof < 0xB` / `type < 0x14`
  are what make an out-of-table type argument a real signal rather than a
  decode error — every constant the tool uses is read from the instruction
  that uses it, not asserted. §§3-4 score the analyser on synthetic hits and
  break it six ways, each of which MUST redden: the control-silent case
  (no base-lookup hit ⇒ rc 2, NO verdict, even with perfect record hits —
  because "it never happened" and "we cannot see it happen" are one picture);
  an armour index resolving to the wrong composite type (refutes P4, the one
  place the record-is-authoritative claim is testable live); a base lookup for
  an ARMOUR type outside step C's table (refutes P1); a type-2 shell alongside
  type 1 and a type-2-only run (both contest §7's "author against type 1", the
  strongest result the probe could return); a reserved-bit index (P5, §9.1's
  namespace); and no armour seen at all (P4 must report NO VERDICT, never a
  vacuous pass). §5 ties the prediction to the content: `OUR_ARMOUR` must be
  exactly what `content/items.toml`'s five rows resolve to through the
  archive's composite table, so editing a content row without editing the
  prediction goes red here instead of producing a run that cannot fail.
  **§§6-8 are the SLOT-CACHE half** (the `cache`/`cachesame` sites and S2–S7,
  which answer whether a costume override REPLACES the armour row or merges
  with it). §6 is the one worth reading, because it is an assertion the
  artifact can refute rather than a list of offsets copied out of a
  disassembly: `m_slotItemData` at +0x24 with a 16-byte row, `m_slotItemId` at
  +0xB4 and the costume override array at +0xD8 are each read from a DIFFERENT
  instruction's own operand — a store displacement, a `lea ecx,[esi+0x2d]`, a
  `mov edx,0x36` — and then required to CLOSE: `0x24 + 9*16 = 0xB4` and
  `0xB4 + 9*4 = 0xD8`, three contiguous nine-slot arrays behind ArenaNet's own
  `cmp esi,9` (`CpsBase:173 slot < arrsize(m_slotItemId)`). It also pins the
  finding that §9.2's "+0x99/+0xA9 dye bytes" are `m_slotItemData[7]+5` and
  `[8]+5` — byte 1 of each costume slot's own row — and that the override
  `or edx,0x20000006` really is opcode 0x81 /1 rather than a MOV, next to the
  `mov [ebp-8],eax` that overwrites the file id, which is why "replace or
  merge" is a per-field question. **§6 also owns BOTH caller maps, and that
  half is new on 2026-08-30 because its absence hid a live defect for five
  days.** `WRITER_CALLERS` had a pinned-image byte check from the start —
  every key must be the byte after a `call 0x0082EDA0` — while
  `UPSTREAM_CALLERS`, which is consumed the same way (looked up against
  addresses walked off `[ebp+4]`), had only dict-membership and count checks
  against fixtures carrying the same literals. NINE of its eleven keys were
  CALL-SITE VAs, which can never equal a return address, so nine of eleven
  could never fire; the two that ever named anything are the two that were
  MEASURED off a live frame rather than read off a disassembly, and that split
  is the tell. The failure mode was not silence — a chain ending on one of the
  nine fell through to "NOT in UPSTREAM_CALLERS — an unlisted path, which is a
  result", i.e. a wrong answer shaped like a finding. §6 now decodes every key
  of BOTH maps out of the image and, for the upstream map, re-DERIVES the two
  caller sets from it: every `call 0x0082D6A0` inside the per-slot worker's
  0x17E bytes (exactly seven of SetSlotItem's forty call sites) and every
  `call 0x004B1800` in the image (exactly two, both listed). `call rel32` is
  position-dependent, so there is no fixed byte pattern to hand-type and aim
  at a decoy — the scan computes targets. All three checks redden on the
  original defect, and the failure detail names the repair ("0xE8 sits AT the
  va … the key wants va+5"). **§7's fixture is the first live run's own
  reading, verbatim** — CpsBase's measured slot order, the override array it
  held, the thirteen rows it wrote — because synthesising a tidier arrangement
  would let the analyser pass on a shape the client does not produce, and the
  tidier arrangement is precisely what S2's first form assumed and the client
  refuted. It then breaks the analyser ten ways: no cache hit at all (rc
  **None**, NO VERDICT — an unwatched row and an unwritten row are one
  picture); a row keeping the ARMOUR record with its override set (refutes S3,
  the single result the run exists for); a costume wire type reaching an armour
  slot's type byte (refutes S4); the head slot keeping tint 19 (refutes S7 in
  the only slot whose value is unambiguous); an unoverridden row that moved
  anyway (refutes S8, the null control); **both** S2 directions — the wire
  identity, which would mean the measured permutation was a fluke of one load,
  and a third arrangement that is neither, each reported as its own case; one
  override id repeated (S6's OTHER branch — a result that moves §9.9's
  reconstruction downstream rather than a failure); an all-zero override array
  (NO VERDICT on S3–S8, because a run without `--costume` and a costume path
  that never fired look identical); and two CpsBase instances, where the
  analyser must score the one wearing our items rather than the
  character-select doll's empty slots. One more guard sits beside them and was
  earned the hard way: `_report` keys its census on captured values, and the
  FIRST live run of these sites trapped everything it was built to trap and
  then died with `unhashable type: 'list'` after the client had exited, losing
  the lot — so the check drives real `_report` over list-valued captures past
  the census threshold. §8 pins `OUR_SLOT_ITEM` to `authsrv.py`'s own
  `STARTER_ARMOUR` source and the slot types, records and dye tints to
  `content/items.toml`, including two deliberately awkward lines:
  `costume_body`'s tint is **0**, which is also what an unwritten row holds,
  so the pin exists to stop the module claiming the body half of S7 decides
  anything; and every armour row already contains the costume override's whole
  flag mask, which is the reason `--armour-flags-clear` has to exist at all —
  if a future row lacks a mask bit that line reddens and the flag can be
  retired. S5's three readings (OR / copy-unchanged / constant assignment) are
  each exercised BY NAME under a simulated `--flags-clear`, because a scorer
  that can only recognise the answer it expects is not a scorer — and because
  the first statement of S5's limit was wrong in a way none of the other
  checks could catch (it claimed the run separated nothing, when the surviving
  out-of-mask bit had already killed the assignment reading).
  **§7b is the CLEAR analyser** (R1-R4, §9.8's reset arms): a clear never
  reaches either row-write exit, so it needed its own site, and the analyser
  is broken five ways -- no clear at all is **NO VERDICT** ("no reset reached
  the client" and "the path is not what was read" are one picture); a row
  write inside a clear burst REFUTES the static reading; an absent record
  fetch reports NOT SEEN rather than passing on an absence; a single burst
  DECLINES the already-empty control instead of scoring it; and with no clear
  site armed the analyser prints nothing at all, so a run that never asked the
  question does not emit a section implying it did. One check pins an ordering
  the first live run earned: R4's window is SYMMETRIC because the notify sits
  three bytes before the trap point, so a clear's own fetches land *before*
  its hit, and a forward-only window silently dropped a whole burst's worth.
  §8 also pins **both costume-head rows** to content and requires them to
  land on DIFFERENT components (2 vs 1) -- if they ever agreed, the second
  row would be testing nothing. Two checks exist because live runs caught
  the analyser over-claiming: S6 now REFUSES to discriminate on a single
  overridden armour slot (where "one id repeated" and "one id per
  component" are the same picture, and it printed the downstream
  conclusion anyway), and S7's body half leans on the observed WRITE ORDER
  rather than on a blanket hedge -- the dye is copied from another slot's
  row, so "was the source written first" is a checkable question and both
  branches are exercised.
  **§9 also carries S9, `row+0x08` = the item's `value`** -- the row's last
  unexplained field (§9.23), and the interesting part of the check is that it
  DECLARES ITSELF WEAK. Every `value` in `content/items.toml` is 0 today, so a
  field the client ignored entirely would score identically, and the report
  says **"PASS, and WEAK BY CONSTRUCTION ... a REGRESSION pin, not a
  discriminating test"** in those words rather than letting a green line read
  as evidence the mapping is right. It is broken BOTH ways: declare a non-zero
  price and S9 reports itself DECISIVE; withhold it from the built row and S9
  REFUTES and reddens the run. One sabotage exists purely for a latent bug the
  all-zero table hides -- `OUR_SLOT_VALUE` is wire-keyed while the analyser's
  rows are CpsBase-keyed, so with every value 0 a missing re-key is invisible;
  the check declares on wire slot 6 and asserts it lands on CpsBase slot 4.
  §8 pins the table to content's own `value` per slot, for the same reason the
  other four tables are pinned there: give one row a price and the prediction
  must follow it.
  **§9 is the FRAME WALK, and it exists because one frame was never going to
  be enough.** §9.13 captured `[ebp+4]` and got `CpsApi::SetSlotItem`, which
  forwards its caller's slot verbatim -- so it names the MESSENGER, and three
  study sections in a row ended on "not identified" while the field that would
  have answered was two frames further out. `walk_frames()` walks the EBP
  chain, and every check here is about it REFUSING rather than inventing: a
  frame pointer that moves DOWN ends the chain (an unwinding stack walks up,
  and a descending link is the shape a garbage read makes); a return address
  outside the code window ends it and NAMES NOBODY; an unaligned pointer is
  refused at the first step; and `depth` is a real bound rather than a
  suggestion. A function compiled without a frame pointer therefore yields a
  SHORT chain, which is readable, instead of a plausible wrong caller, which
  is not -- `studies/heroes` §36.6 is the entry that rule is paying for. The
  ordering is now SCORED per instance rather than read by hand out of a
  timeline as it was in §9.11 and again in §9.17, and the check that matters
  is the AMBIGUOUS one: an instance holding only slots where the two orderings
  AGREE is credited to neither, without which every short instance would read
  as confirmation of whatever the reader expected. An item id belonging to no
  slot in either ordering is NEITHER rather than silently absent, and an
  instance whose chain never reached the upstream says **upstream NOT
  CAPTURED** rather than omitting the line, which would read as "no upstream
  involved". The two addresses the live run produced are pinned by name --
  `0x004EEC34` GmDoll and `0x007F9F5F` AvChar (§9.21) -- next to a check that
  the map is a NAMER and never a FILTER: an address in the code window but not
  in the map still reaches the report, or the one path nobody predicted would
  be the one path a run could not show.
  Needs the pinned exe for §§1-2/§6 and the vault for §5, all SKIP-declared;
  a whole green run is 105 (102 before the two caller maps got their image
  checks) and the floor is **78**, its MANDATORY CORE -- lowered from 76/80,
  which sat ABOVE it, so a machine without a vault would have failed on the
  floor instead of reading four honest skips and the shortfall would have
  named the wrong thing. **That bare-machine path had never been WALKED until
  2026-08-30**, and it did not work: `pinned.find()` raises `SystemExit`,
  which §1's `except Exception` does not catch, so an empty `RURIK_VAULT` gave
  rc=1 and no verdict rather than a skip. Now measured rather than reasoned --
  83 checks, 2 declared skips, rc=0 -- which is why 78 stays where it is),
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
  pass the vacuity check alone. §4 pins the WIDE-STRING CAPACITY, a twice-
  documented display defect (`Field.__repr__` prints `self.cap` and the `wstring`
  branch passed no `cap=`, so all 141 wide strings read `string16(0)`) that was
  fixed in `c81d6d1` and then sat four days with two study docs still calling it
  open — a fix nothing pins reads exactly like a fix nobody made. It asserts the
  capacity histogram over all 141 fields on each vaulted build, identical across
  the three (§2's claim from another direction), and two opcodes whose capacity
  has an INDEPENDENT witness: `0x01BF`'s `string16(20)` in 50 B corroborating
  GWCA, `0x0074`'s `string16(32)` in the 127 B that refuted the upstream 4-field
  reading — the wire total being the half a wrong capacity cannot fake. Its
  negative control builds a `Field` the old way and asserts it STILL prints
  `string16(0)`, so dropping `cap=` again reddens 14 checks; verified by doing
  exactly that. Needs the vault throughout. Floor 73, ~75 s),
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
  ships is one somebody deletes.
  **§7 AND §8 ARE THE DIGEST SET, added 2026-08-19, and the gate they cover had
  gone INVERTED.** "Our patched copy" was ONE hand-typed sha256 of ONE whole
  file, and a whole-file hash of a patched binary goes stale the moment the
  patcher changes. It did — the key-tap added three sites (file `0x508E2`,
  `0x50905`, `0x3DB4CE`) — so the gate REFUSED the freshly patched client at
  `vault/run/2026-07-29_221c13772c7a/`, the copy we launch and the one
  `movetap.py`:438 gates, while ACCEPTING the two superseded copies at `-c2/` and
  `-probe/`; build 38833 had no patched hash at all, so the newest build was
  unrepresentable, and the only way past either was `--any-build`, which turns a
  gate off rather than fixing it. `Build.patched` is now a TUPLE of
  `PatchedCopy(sha256, how)` and **the patcher appends its own digest** into
  `vault/client-patched/patched_digests.json`, so registration is a step in
  building the client rather than a chore nobody was ever going to do by hand on
  patcher-change day. sha256 is still exact — there is simply more than one right
  answer — which is why this was chosen over a structural allowlist: an allowlist
  accepts ANY bytes at an allowed site, and the most consequential bytes in the
  file, the Diffie-Hellman modulus that decides which server a build may be
  pointed at, sit at one. §4 now asserts both directions against the real files
  (the current copy passes AND the two stale ones still do, because fixing it by
  dropping the old digest would have inverted it the other way), and pins the
  structural evidence the refusal quotes: our patches are 6–9 differing runs from
  pristine, `run/reskin-roster/` — a real client of the right build — is **211**,
  and the other build at the same length is **152,735**, which is what tells an
  operator "ours, unregistered" from "not this build at all". **That third figure
  read 152,944 until it was re-measured**, and the correction is small but it is
  the kind this module exists to make: 152,944 is `run/reskin-roster/Gw.exe`
  against 38833's pristine — an outlier copy against the wrong build — printed as
  a property of the two BUILDS. Pristine against pristine is 2,613,239 bytes in
  152,735 runs, §4 now re-measures exactly that pair, and every cross-build pair
  in the vault falls in 152,735–152,944 (n=9), so nothing resting on it moves —
  but it is the one number in that refusal that is not computed from the file in
  hand, and a number a message quotes and nothing re-measures is the same wish as
  a rule nothing checks. §7 runs the whole
  registration cycle against a FAKE vault so the real one is never written: the
  refusal fires on an unregistered right-sized file FIRST, the same file is then
  registered through `register_patched()` and accepted, and the reason must NAME
  which source vouched — the reproduced stale-hash configuration, where the
  build's committed digests do not contain the file and the set does. Its
  controls are every way the new write path could have widened the gate —
  registering the pristine image, a wrong size, a file 200 runs out, an unknown
  build, a CORRUPT registry (which must read as unreadable and refuse, never as
  empty and silent) — each with a positive half, because a `register_patched`
  that refuses everything puts the staleness back by another route. §8 asks the
  SYNTAX TREE whether `make_custom_client.py` and `make_run_dir.py` actually call
  it, and call it AFTER they write: neither had any such call until this round,
  and "registers after writing" greps identically to "registers before writing",
  so the checker is required to reject both a reversed and a call-less patcher.
  It also pins `build_arg`, which was a live defect the first time `--register`
  ran: argparse hands back text, so `--build 38797` reached `select()` as the
  STRING it refuses on purpose, and the CLI answered "no such build in the vault:
  '38797'" while listing 38797 in the same sentence — the lookup keeps refusing
  and the coercion sits at the argv boundary.
  **§9 IS THE ADVERSARIAL PASS OVER §7's OWN CHANGE, the same day and after it**,
  and every check in it is an attack that SUCCEEDED against the morning's code and
  was measured before it was fixed. Appending a digest set stopped the gate
  refusing the client we launch; it also made "register" a verb the gate honours,
  and there were four ways to say it about the wrong bytes. **10,483,904 bytes of
  `os.urandom` registered under `strict=True`** and `assert_build` then called them
  patched, because with no pristine image on disk `diff_against_pristine` answers
  `(None, None, why)` and the sanity bound read `if nruns is not None and … and
  strict` — SKIPPED in the one configuration where nothing else can tell a patch
  from a stranger, and `find()` documents that configuration as supported while
  `make_run_dir.py` registers on every run. **ArenaNet's own pristine 38833 image
  filed as our patched 38797**, because only the SELECTED build's pristine was
  compared and the two builds are the same length; the refusal now covers ANY
  known build's pristine and has no `--force`, since there is no legitimate
  reading of the shipped binary as one we made. **A registration whose write
  FAILED was honoured by the gate for the rest of the process** —
  `action='refused'`, no file on disk, accepted digests 3 → 4, `assert_build`
  "patched" — because the row was appended to the list cached in `_registry`
  before the write was attempted; it is built into a new list now and the cache is
  dropped on the error path, so the module's stated fail-closed design is what the
  code does. And **registry rows are validated on read**: a truncated digest, or a
  row whose `build` and `stamp` name two different builds — which
  `accepted_patched` matches on EITHER, so one such row vouched under BOTH — is
  dropped and counted in `why` rather than honoured. Each has a positive half in
  the same block (the deliberate `strict=False` path, a file that is nobody's
  pristine, the same call with the write unblocked, a well-formed row), because a
  `register_patched` that refuses everything puts the staleness back by another
  route. §8 gained that pass's two CALL-SITE halves: the build handed to
  `register_patched` must not be one the patcher chose — it was `build=tag`, a
  regex over the source exe's **filename**, and `CLAUDE.md` says never select a
  build by filename — so the bytes decide and the tag is a cross-check that must
  agree or the registration is refused; and `import pinned` must sit inside the
  same `try/except` as the call, since both patchers call the registration
  "NON-FATAL, deliberately" in a comment and neither enforced it. Both carry
  controls in both directions, because `build=tag` and a module-level import grep
  identically to the right thing. §4's attribution check was rewritten in the same
  pass: `"committed in pinned.BUILDS" in detail or "vault registry" in detail`
  cannot fail under its own `what == 'patched'` guard — every patched detail ends
  `[{acc.source}]` and that source always begins with one of exactly those two —
  so it now asserts the NAMED source is the list the digest is really in.
  Without a vault §4 skips and the run scores 109 against a floor of **130**, so
  it goes red — **and until this pass it did not**. The old floor of 104 was
  arrived at by subtracting the optional checks off a full vault's total; an empty
  vault scored 109, five ABOVE it, so the sentence promising a red run described
  something that never happened (and the same comment said "8 of the 112" for a
  114-check run). The floor is now MEASURED on a minimal legitimate vault —
  `client/<stamp>/Gw.exe` for all three builds and nothing else, a machine that
  snapshotted its install and never patched a client — which scores 130 with 1
  declared skip. The full vault scores 143; the 13 extra ride on copies a
  legitimate vault need not hold (`run/<stamp>`, `-c2`, `-probe` and the patched
  38833 copy at 2 checks each, the two `run-live` copies at 1 each, the patch-bound
  and reskin measurements at 3 between them). The cross-build distance check above
  moved it 129 → 130 rather than into the 13, because it needs only the pristine
  images. ~6 s),
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
  claim and declares one skip, so the stdlib floor is unmoved.
  **§12 (2026-08-26) is the defect a FOURTH time, and this one arrives by a new
  road: not "which encoding of the constant" but "which WIDTH of the field".**
  `--bit DISP:N` exists because bit 18 of the dword at `+0x20` **is also bit 2
  of the byte at `+0x22`**, and MSVC narrows `flags |= 0x40000` to
  `or byte [esi+0x22], 4` as a matter of routine — an instruction carrying
  neither `0x20` nor `0x40000` anywhere in its bytes. §12a pins the derivation
  (`bit_views`) rather than the search, because the derivation is the part that
  makes a zero honest. §12d is the census that the MOVECODE arc rests on:
  **exactly one `or dword [reg+0x20], 0x40000` in the whole 5.4 MB .text
  section**, at 0x005FE56C, with the glide-vs-teleport branch 0x0060029F among
  the memory-form reads — a pin that reddens if a future anchoring change drops
  the site or invents a second. §12e pins two classifier bugs the instrument's
  own first run produced and that a filter-shaped `--field` would have produced
  too: `test dword [edi+0x20], 0x10000` tests bit **sixteen** and
  `and dword [edi+0x20], 0xfffdffff` **preserves** bit 18 while clearing 17, and
  both were reported as bit-18 sites until every branch was made to decide on
  whether the mask actually covers the bit. Non-covering rows are now reported
  as NEIGHBOUR rather than dropped, which is what named bits 16/17/19 of the
  same word. §12b is the falsifiable half and goes red in BOTH directions: the
  phantom filter is scored on eight addresses established by hand, three of
  which are **not instructions at all** — `d9 5c 24 04` is
  `fstp dword ptr [esp+4]` and its trailing two bytes decode alone as
  `and al, 4`, which put three phantom "reads of bit 18" into the first run
  indistinguishable from the one real site. A filter that calls everything real
  fails the first three; one that calls everything phantom fails the other five.
  It is anchored on a decode from the function's own `int3` boundary, because
  merely asking whether SOME nearby decode reaches the address is not enough —
  searching 96 starts, 0x00600FD4 aligns from 0x00600FCE as four plausible
  instructions of pure coincidence. §12c pins `--upto`, which recovers the
  instructions ENDING at a VA by consensus search instead of a guessed start;
  a guessed `--dis va-0x20` returned confident garbage
  (`add byte ptr [ebx - 0x7c76f3bf], cl`) for two of five call sites being read
  for their pushed arguments, and the `push 0` it recovers at 0x00602A7F is the
  hardcoded `isWaypoint` the whole arc turns on. 135 checks with capstone (was
  116) and 45 without — §12 declares one skip, so the stdlib floor is unmoved),
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
  are proved to have passed condition 2 rather than skipped it. **What that did NOT
  prove until 2026-08-17 is that the build is TRUE**: it was `pinned.BUILD`, so rows
  read out of any client claimed 38797 and every check above passed, `content.py`
  included — the gate asks that a build be present, not that it be right. The
  fixture made it invisible by handing the emitter the literal string `"TEST"` as
  the path it had read, which the constant did not care about; it passes `pe.path`
  now, and §8 emits a second time from the 38833 client and requires the stamp to
  MOVE. The emitter refuses outright when `buildid.of_image` cannot name the build,
  rather than writing the usual answer onto a row whose whole purpose is being
  re-derivable. `heroes_table.py` had the same defect and `test_heroes_table.py` §4
  checks it the same way. Sections 0-4 build a
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
  draws. **68/7 is the founding measurement and not today's**: the census pin is
  a literal in the test and it is **233 across 21 files** as of 2026-08-29, with
  1,812 prose citations and 446 test expectations — and note what this line's own
  history says about itself, because it is the point. It read **99 across 14
  files** for ten days and six census moves (113, 134, 135, 151, 156, 189, 204),
  wrong the whole time, because **no test asserts a number in prose**. The two
  test literals are on everyone's checklist and this sentence was on nobody's;
  that is the same failure the changelog records against the literals themselves,
  with a document standing in for the second witness. It had been RED at 86/13 —
  `framebus.py` 13 → 21, `movetap.py` 0 → 1 (`RVA_TLS_INDEX`, and the 14th file)
  and `pinned.py` 8 → 12 (`PATCHED_TEXT` gaining the key-tap's cave and jump when
  the patched-digest set was added). The docstring's changelog names each, which
  is the format that makes a moved census a result rather than a surprise. No
  vault, no client, no socket. Floor 40, ~2 s),
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
  because the count was self-consistent.
  **§10 (2026-08-31) lints `LEDGER.skip` ARITY across the tree.** `Ledger.skip`
  takes `(label, why)`; seven files across four packages called it with one
  argument, so each raised `TypeError` instead of declaring the skip. None had
  ever executed: every such call sits on the branch a machine takes when a
  resource is MISSING — no vault overlay, no capture corpus, no pinned build —
  and the suite runs where those exist, so the skip paths were dead code that
  read as diligence. `test_castcycle.py` promised a bare machine in its
  docstring and died in a traceback instead, which is neither a measurement nor
  a verdict. This is a shape a linter can settle and a run cannot, since
  reaching those branches means removing the vault. Its CONTROL plants a
  one-argument call and requires that the correct two-argument call and a
  non-Ledger `.skip` are BOTH left alone — a false positive here is worse than
  a miss, per the top of that file.
  **§10's detector was REWRITTEN the same day, and the reason is this section's
  own lesson arriving late**: it matched receivers whose NAME contained
  "LEDGER", and `test_trnblend.py` writes `led = checks.Ledger(...)` — so five
  one-argument `led.skip()` calls sat under a green §10 for the day between the
  two. It now collects every name the module BINDS to a `Ledger()` and judges
  `.skip` on exactly those, and the control gained a lowercase-`led` line so it
  fails on that regression instead of blessing it. A linter's own blind spot
  reads exactly like a clean tree — §4's complaint, in a check §4 does not cover.
  **§11 (2026-08-31) is the same "the fallback never fires" defect one level
  down: a handler that guards a `SystemExit`-raiser but catches only
  `Exception`.** `vaultpath.require_dir()`, `pinned.find()` and
  `skilltable.find_exe()` all RAISE `SystemExit` when the resource is missing —
  deliberately, so a tool dies loudly rather than reading the wrong build — and
  `SystemExit` inherits `BaseException`, so `except Exception` never catches it.
  **Nineteen try-blocks across four packages** did exactly that, and every
  fallback behind them was unreachable on the only machine it was written for:
  fourteen `LEDGER.skip`s, a friendly `TapeError`, three `return None`s and one
  default path. `test_compositetrap.py` §1 and `test_agentlife.py` were the two
  found by running into them; §11 finds the rest without a bare machine.
  **`vaultpath.vault_path()` is deliberately NOT in its list** — it returns a
  path for a directory that does not exist and raises nothing, so its 21 call
  sites are not defects, and scoring them would have made a 40-site "finding"
  that was 21 parts wrong. The control checks both directions: the narrow
  handler is caught, the widened form and a `vault_path()` call are not.
  **AND §11 IS A FLOOR, NOT A CENSUS** — say so before trusting it. It reads a
  try-block body for a DIRECT call, so it is blind to two shapes the same sweep
  found only by RUNNING the files: a locator called with **no try at all**
  (`test_itemmods.py`'s `pinned.find()` opening `main`, which killed the file
  before five carefully-worded skips below could run) and an **indirect** call
  through a wrapper (`test_wearmap.py`'s `composite.extract()`, which reaches
  `pinned.find()` inside). Both are fixed; neither would have been found here.
  Floor 22 → 24 → **26**),
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
  there is the skip it now declares. Floor 40, the MEASURED vault-less score; 41 on an
  overlay with no extracted-source row, 43 with one. It was 39 until 2026-08-20,
  when WORLDMAPS-W3's `[map.166]` was NAMED here rather than absorbed into the
  count -- the migration section pins the exact SET of map ids and its own
  comment says why ("the table grew" and "a row changed meaning" look identical
  to a length check), so a created row costs one named check and one line of
  prose about what makes it a different kind of row),
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
  floor to 19; 2026-08-20 took it to 20 for the created/retail split, which runs
  before any archive is opened, and the residual pass took it to 29 for §6.
  **§6 is the ORDERING, and it is this file's own original defect seen from the
  other side: a question answered against the wrong half of the pair.** The
  created-row SKIP was decided from the CLIENT's table alone -- `s_tab` is built
  at the top of `check()` and first consulted twenty lines past a `continue`
  this row could never come back from -- so a chain allocated into the SERVER's
  archive and not the client's read as the benign pre-creation state and refused
  nothing, while the server would send a map id whose file the client cannot
  bind (`Code=007`: loud on the client, silent in the server log, the shape that
  costs a session to diagnose). The server is consulted FIRST now. A skip needs
  BOTH sides empty and says "NEITHER"; the server alone binding it is FATAL,
  naming the server's row and saying which state it is NOT, because the whole
  failure was one state reading as the other; an unreadable server archive is a
  skip naming the question it could not answer, since "not made yet" is a claim
  about both copies. §6 is SYNTHETIC like §5 -- it drives `check()` over
  hand-built tables keyed on the archive PATH, since `check` asks the client's
  half `raw=True` and a stub keyed on the flag alone would answer the same for
  both -- so it cannot skip, it joins the mandatory core, and no real vault can
  be made to hold this state on demand. Seven cells, each one fact apart from
  its neighbour (neither, server-only, both-same, both-different, client-only,
  server-unreadable) plus the CONTROL that a NON-created row the client cannot
  bind was always fatal and still is, by the older sentence -- so what moved is
  the created branch alone. Sabotage driven by hand, red: reading the server
  back AFTER the skip decision reddens 3.

=== FOR THE COMMIT MESSAGE (the WORLDMAPS residual pass and its fix, 2026-08-20, offline) ===

- Floors moved, every one MEASURED from a real green run and never projected: test_deploy 167 -> 203 (199 vault-less, exit 1 naming the 4-check shortfall -- which is what the floor is for); test_contentids 20 -> 29 (a green run scores 40 with 2 declared skips); test_datwrite 199 -> 212.
- Tests run and their counts: test_deploy (203), test_datwrite (212), test_contentids (40/2 skips), test_mapscale (62/1 skip, it imports deploy read-only), test_srclint (22, it lints the whole tree), and as collateral on the datwrite change test_overlay (133), test_datmove (46), test_datalloc (203). The full suite was NOT run, per the house rule.
- datwrite is safety-critical and the change is a TYPE, not logic: `_grow_gate`'s four raise sites become `GrowGateRefused(condition, ...)`, a `SystemExit` subclass. Every message, every condition, their order and the exit code are byte-for-byte unchanged; the machine-readable `GROW-GATE-REFUSED condition=<name>` line is printed by `main()` BESIDE the refusal and never inside it, because an exception class does not cross a subprocess boundary and `deploy.py` reads bytes.
- New in deploy.py: `head_is_armed()` (R1, the guard factored out of main so it can be asked), `alloc_journal_path()` / `allocation_recorded()` / `created_evidence()` (R2) and `archive_carries()` (R2's fix). `resolve_or_create` gains keyword-only `here=`/`tag=`, fail-closed. `main()` hoists `out`/`here` above the archive block -- same expression, depends on nothing the archive says -- and threads them.
- THE R2 EVIDENCE CHECK JOINS ON BYTES, NOT ON A FILENAME. The first version compared the absolute path `datalloc` records against the archive's, which refused an honest re-deploy of our own chain on any whole-file COPY of the archive -- and copying a Gw.dat is routine here (`overlay.py`, `make_run_dir.py`, RUNBOOK's `Copy-Item`). It now accepts EITHER the recorded path OR the archive still carrying the file-id record the journal wrote, at the offset it wrote it. Each of the four conjuncts has its own fixture; a mutation sweep over all of them is in test_deploy §10b's comments.
- Behaviour changes an operator will meet: a `created = true` row whose id already binds REFUSES without an allocation journal that describes it AND is bound to this copy; a create whose `<area>_alloc.json` exists REFUSES; and a created id bound in one archive and not the other is FATAL in the pre-flight rather than a skip, which will fire the first time W7 deploys the chain into one copy and launches against the other. All three name their remedy, and the first now names the recoverable one (bring the journal to the archive) before the last resort (allocate under a fresh id).
- Every vault touch was READ-ONLY: two build-only `deploy.py` runs (plaza, frontier) and the two test files' own archive reads. No client was launched, no archive was written, no commits were made.
- Known flake, not a regression: one mid-session test_contentids run went red on §1's "the check produced findings at all" with both halves reporting the client archive unreadable -- the 4 GB archive was momentarily held open by another session, which is the hazard §1's own comment describes. Readable a second later; the re-run was green. **A CREATED content row is a third state and it
  nearly deleted this guard**: `[map.166]` names a file id that binds nothing
  until `deploy.py --install` allocates it, so `check()` returned FATAL for every
  archive and -- with `served=None`, the fail-closed default that tape runs and
  every un---map-ped run take -- that one row refused EVERY loopback launch in
  the repo, which is precisely the 2026-08-15 false positive this file's own
  docstring warns about. `contentids.check` now records an absent created id as a
  printed SKIP and judges it normally the moment an archive binds it, and this
  file holds the created rows OUT of both archive-selecting scans: section 2
  picks its positive control with `any(f not in raw for f in ids.values())`,
  which is true of EVERY archive once a created id exists, so it silently
  selected the wrong archive and four checks went red naming Pre-Searing while
  the code under test was fine -- a fixture resolving to the wrong thing, which
  is the defect `vaultpath.require_dir()` exists to prevent one level up. The
  two new section-1 checks are gated on `check()` having returned findings at
  all, because these are 4 GB files another session may hold open. The check that
  matters most is the fail-closed one

FOR THE COMMIT MESSAGE (updated by this fix pass where the numbers moved):
- test_deploy floor 56 -> 92 across the two passes. MEASURED green runs 2026-08-20: 92 with the vault, 88 without (RURIK_VAULT pointed at an empty directory, section 2 skips, exit 1 -- which is what the floor is for). Section 8 adds 36 checks in total: 28 from the build pass, 8 from this fix pass (4 on `create_note`'s states, 2 AST pins with a sabotage, 2 on `spill_stream`).
- test_content floor 39 -> 40; a green run scores 43 with the vault overlay (re-confirmed today).
- test_contentids floor 19 -> 20; a green run scores 31 with 2 declared skips (re-confirmed today).
- Fixture change worth naming: test_deploy's hand-laid archive declares 16 rows rather than 6, so an appended chain lands at index >= 16 (FIRST_CLAIMABLE_ROW). Section 7 is unaffected and still green.
- content/maps.toml [map.166] and content/areas.toml [area.frontier] are the only content rows added; nothing else in content/ moved, and this fix pass did not touch either.
- New in deploy.py from this pass: `create_note()` (the row line, printed on every run) and `spill_stream()` (shared by both write paths). `install_partner`'s stored/compressed branch became one line through the helper; behaviour on that arm is unchanged.
- Every vault touch in both passes was READ-ONLY: the C2 copy was read for `plan_alloc`, for the step-1 dry run and for the donors. Nothing was written to any vault archive, no client was launched, and datalloc.py/gwenc.py/datwrite.py/datmove.py were not modified.
- Tests run this pass: test_deploy (92, green), test_srclint (22, green -- it lints the whole tree, so any source edit is its business), test_content (43) and test_contentids (31/2 skips) to confirm the RUN note's precondition counts. The full suite was NOT run, per the house rule.: an EMPTY set
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
  agreeing and calling it evidence. **§§0-18 need no vault, no client and no
  socket** — the content store and pure arithmetic — which is why the floor can
  be their whole count rather than a guess; §19 and §20 came later and read the
  client image, so "nothing here can skip", true when written and stated flatly
  in this entry until 2026-08-18, is now only true of the part the floor covers.
  §7 pins the two field widths APART -- `0x0080`'s dialog line is
  `string16(122)` and `0x004C`'s description is `string16(128)`, six units
  distant, and the check that earns its place is the one asserting a line which
  FITS the description field is REFUSED for the dialog one; a single shared
  constant would pass everything else and put that error where only a screen
  could find it. **Floor 73 against a healthy 83 with the vault present, 73
  without** (it read "a healthy 77" until 2026-08-27) — §19 re-derives 888
  from the client image, §19b is new, and §20 re-checks the
  twelve cited sites across builds, so those sections declare skips on a
  machine with no vault (§20 also skips
  on fewer than two vaulted builds at or after the pin). 73 is what remains
  when they all stand down, which is where the floor sits and why adding a
  vault-gated section never has to move it. **§19 GREW ON 2026-08-27 AND §19b
  ARRIVED, because §19 was scoring one of two names for the same quantity and
  the other one was WRONG.** `authsrv.MAP_ID_COUNT` was 877 — OpenTyria's enum
  end, UPSTREAM, never read off a binary — and it is what the first
  `MANIFEST_DONE` of every login burst carries as the "no map" sentinel. Row
  877 is a real populated row on this build (`Forsaken Tunnels: Level 2`), so
  the server's "no destination" named an actual dungeon, while `NO_MARKER_MAP`
  sat at a correctly re-derived 888 twenty lines away and this section stayed
  green because it only ever asked about that one. §19 now scores **both**
  names and their identity; `NO_MARKER_MAP` is *defined as* `MAP_ID_COUNT`, so
  the quantity is expressed once in code instead of as two literals that drifted
  apart for weeks. **§19b is the part that makes it a measurement rather than a
  coincidence**: it scans every vaulted client for
  `mov dword ptr [reg+0x134], imm32` — the store the manifest's own map argument
  lands in, reached as `[ebp+0x10]` at `0x0085222E` — and requires five sites
  per build with the immediate tracking the map table: **883 on 38519, 888 on
  38797/38833/38849**, ArenaNet having added five maps in between. An older
  build reading a *different* value is asserted too, because without it "every
  build stores 888" could be true of any constant in the image. **And the
  control is the half that kills 877**: the same scan must find `0x36D` as a
  compare bound **zero times on all four builds**, which it does — so 877 has no
  client witness anywhere and the real sequence is 883 → 888 with OpenTyria's
  enum end naming nothing between them. Full record at
  [studies/maprows/FINDINGS.md](studies/maprows/FINDINGS.md) §10, including the
  honest gap: nothing in MsCliMan *reads* +0x134, so the consumer was not chased,
  and no login has run since the flip. **AND 73 IS NOW A MEASURED NUMBER
  RATHER THAN AN ARITHMETIC ONE, which it was not until 2026-08-18**: it was
  77 minus the four vault-gated checks, sound as subtraction and impossible to
  observe, because TWO separate defects stopped a bare run before the verdict.
  `import authsrv` (line 34, added by `5ab72e4` — the same commit that wrote
  this floor) reached `probes.py`'s module-level `npc_template("def_1480")`, a
  vault-only row, so the run died at IMPORT and never reached check 1 of the 73;
  see `toolkit/test_bareimport.py`, which now guards exactly that. With the
  import fixed §19 still killed the run, because `pinned.find()` reports a
  missing build by raising **SystemExit**, a BaseException that sails through
  `except Exception` — so the skip that this paragraph credits it with was
  unreachable, and a skip that cannot be reached is the same defect as no skip
  at all. That is the identical failure `test_skelwrite.py`'s entry records at
  the end of this file (`require_dir` raises SystemExit past `except
  Exception`), hit twice in two files, which is what makes it a shape rather
  than an accident. Both except clauses now name SystemExit, and a bare run
  scores **73 with 3 declared skips, green** — measured, not derived.
  **This entry said "a healthy 74"
  until 2026-08-18**: 74 was the count before §20, which landed hours after
  the recompute in `d0b97b9` — the same commit that wrote §20's paragraph
  above and left the figure two sentences away from it untouched. It was
  **17 against a run of 22** when written, with a careful on-paper
  derivation — 13 row-independent checks plus 4 per row — and the file then
  grew to 74 against the same one-row table while the floor stayed at 17, so
  a healthy run did four times its own minimum and three whole sections could
  have vanished unnoticed. That is the failure `checks.py` exists to refuse,
  arriving by growth rather than by a bad guess, and the lesson was that a
  DERIVED floor goes stale silently where a measured one goes stale loudly.
  Recomputed 2026-08-17 from a real green run — and then the healthy count
  beside it went stale silently anyway, because `checks.py` can only make the
  number in the CODE go loud. Nothing reads this paragraph, so when a section
  lands, the figure here is the one to re-measure by hand.
  §§17-19 are rung Q6: that the replay uses `0x0050` and never `0x0049` (whose
  body writes `charContext+0x528`, silently making the last quest pushed the
  active one), that `0x004C` precedes `0x0054` — **deliberately NOT ArenaNet's
  order**, since the client gates the objectives line on the description-filled
  flag and ArenaNet trips its own gate twice in the corpus — that the stale
  marker clears to `(+inf, +inf)`/888 and never `(0,0)`, and that the progress
  carrier shares `quests` across connections while deliberately NOT carrying
  `desc_sent`, whose survival would make every objectives line after the first
  map a silent no-op. **§20 is the 38797→38833 re-check**, and it is the section
  that turned FINDINGS §7.9's *"probably did not move; 'probably' is what the
  VA-drift rule exists to refuse"* into a measurement: twelve cited sites read
  byte-identically on the pin and on the build the owner runs, and the frame-bus
  pairing holds 11 of 11 on both. **Its CONTROL is a whole build.** A first draft
  asserted identity across ALL vaulted images and went red — correctly — because
  **38519 is ~90 days older and 0 of 12 sites match there, with the frame-bus scan
  finding nothing in any quest body at all.** So the claim was rescoped to what was
  actually measured (nothing moved across the 15-day 38797→38833 patch, which is
  much smaller than "stable"), and 38519 became the control proving the equality is
  a measurement rather than a reader that never opened a file. A fourth vaulted
  build is covered with no edit. Needs the vault and two builds at or after the pin;
  skips loudly otherwise. ~2 s, ~40 s with §20),
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
  `toolkit/test_seclint.py` (an ACCUMULATION TRIPWIRE on SECTION-NUMBER collisions --
  two headings that both took "the next number", so every later `§N` citation is
  ambiguous. Written 2026-08-22 after `studies/skills/FINDINGS.md` did it TWICE: §26
  first, resolved as §26.12/§26.13, then `## 32.` for both the silent-extend probe and
  E10 on 2026-08-21, with `PLAN.md` §8's adrenaline entry citing "§32" and meaning E10.
  Nothing caught either; a human reading PLAN.md caught the second. Disjoint from
  `test_identlint.py` by construction -- that one's token must be letter-led
  (`[A-Z]{1,2}-?\d{1,3}`), so a bare `## 32.` matches none of its definers, verified.
  **The SCOPING is the whole design and it was measured, not assumed.** The naive rule
  -- no number twice in a file -- reports **74 duplicates across 11 files** in this tree,
  and nearly every one is correct house style: a dated pass that restarts at §1 under
  its own `#` divider (skills, isle, review, character all do it), and `### N.` lists
  under different `##` parents (`studies/movement/FINDINGS.md` has SEVEN `### 1.`
  headings, all fine). A checker red on those is one nobody leaves switched on, which is
  the lesson `test_provlint.py` records from the strict side. So a collision is two
  headings with the same token, at the same level, under the same chain of enclosing
  headings -- **6 in 2,102 numbered headings**, each named in `KNOWN` with its reason.
  **Its POSITIVE CONTROL is the real defect, rebuilt from the live document**: it renames
  today's `## 36.` heading back to `## 32.` in memory and asserts the collision is
  caught, and that it is the ONLY thing reported about that file -- so the §1-§8 pair in
  the same document stays green, which is the point of the scoping. A frozen fixture
  would drift; this cannot. Section 2's four negative controls are load-bearing for the
  same reason. Diverges from `test_identlint.py`'s count-CEILING posture deliberately:
  53 collisions are too many to justify one by one, 6 are not, and inside a ceiling of 9
  three could land unseen. The known list is checked in BOTH directions -- a new one, a
  known pair gaining a third claimant, and a STALE entry the scanner no longer finds all
  fail -- and each of those three verdicts has a control that doctors the list and proves
  the verdict speaks. **The 6 are NOT a fix list**: `studies/idents/HANDOFF.md`'s star box
  refuses a mass rename of existing tokens, section numbers are load-bearing in commit
  subjects (`Skills 32.8`, `Isle 8.6`, `§27.4`), and one of the 6 -- heroes §35.2 -- is a
  deliberate SUPERSEDED-BY banner above the heading it supersedes and must not be
  "fixed". No vault, no socket, no client. ~1 s),
  `toolkit/test_identlint.py` (an ACCUMULATION TRIPWIRE on IDENTIFIER collisions, the
  same posture as `test_provlint.py` and chosen the same way. `studies/idents/HANDOFF.md`
  §3 decision 5 offered three shapes — a hard gate refusing any new token without an arc
  prefix, a tripwire that only reports GROWTH in the collision count, or documentation
  and no checker — and the middle one won on the argument that file's own top box makes:
  eighty study documents predate any convention, a gate over them "will produce a red
  suite for reasons nobody wants to fix at 2am", and the last time this repo read a rule
  literally across sixteen documents it rewrote 46 citations and **reverted all 46 the
  same day**. So `identlint.py` counts and never judges, and the ceiling lives here.
  **A collision is not a defect to be scrubbed**: 53 of them are the tree's current
  ruled-on state and a mass rename is refused in advance; the defect is the 54th
  arriving unnoticed. Baseline **312 defining sites across 31 documents, 152 distinct
  tokens, 53 colliding** (2026-08-20, after the token pattern widened to admit the
  convention's own shapes — `GATEFIRE-C3`, and ladder rungs like `R-ISLE`/`R-IDENTS`,
  which a pre-merge review found the resolver blind to), ceiling **80** — 53 at the same ~1.5x
  headroom `test_provlint.py` used for 134→200 and 280→420, not a new rule, and raising
  it when it fires is a normal edit. **It fired, and was raised 80 → 132 on 2026-08-31
  against a measured 88** (640 sites, 64 documents, 277 distinct tokens). The 88 were
  READ before the raise, which is what the failure text asks: 78 are bare letter-series
  (`A1`, `C13`, `D12`) — the gap `studies/idents/CONVENTION.md` exists to close and
  grandfathers — and the other nine are NORMALISATION artifacts rather than ambiguity:
  `ANIMREF-R5`, `MORALE-P1..P4` and `MOVECODE-B2` are correctly prefixed and collide
  only because a study's FINDINGS.md and PLAN.md both cite them, while `R4A/R4B/R4C`
  are the hyphen-digit truncation the tool's own notes call out as able to MANUFACTURE
  a collision. None is the 2.2(a) defect. **132 is this entry's own ~1.5x rule applied
  to 88 — the same headroom that made 80 out of 53, and `test_provlint.py` out of
  134→200 and 280→420 — so it buys roughly five arcs at ~9 collisions each.** It was
  briefly 90 earlier that day and moved because 90 left 2, and the rationale beside the
  constant already records re-arming *three* short as a mistake that "fires on the next
  session's ordinary work": a tripwire re-armed inside its own noise is a false alarm
  with a delay, not an early warning. A "defining site" is only a table row or a heading
  that OPENS with the token, because §2's census pattern was table-rows-only and this
  one is still a FLOOR: prose definitions, bold list-leads (`- **C6** — …`), mid-heading
  references, `RUNBOOK.md`'s F-namespace and §2.4's bare-integer commit prefixes are all
  outside it, and `identlint.census_limits()` prints that list in the tool's own output
  so the caveat cannot drift away from the number the way §2.1's own 108 did. **Section 2
  is the load-bearing one** — nine REFERENCE forms that must not count, because every
  study doc is built out of citations of other arcs' tokens and a census of mentions
  measures cross-citation rather than ambiguity; the sharpest case is `studies/idents/`
  itself, whose census tables are nothing but backticked citations and which must
  therefore contribute **zero** sites. Section 4 proves BOTH arms rather than asserting
  the tree is clean today: the comparison goes red one collision above the ceiling, a
  synthetic rival definer added to the REAL scan moves the count by exactly one, and a
  second definer in the SAME document does not — one arc numbering its own table C1–C9
  is a namespace working, not a collision. The control token is chosen at run time (the
  first plain LETTERS+DIGITS token defined in exactly one document — the shape filter
  is what guarantees the synthetic definer round-trips the scanner), so the growth arm
  cannot rot into a mid-run abort the day an arc mints a rival of a hard-coded one. Section 5 is the deliverable:
  `whichrung.py` resolves `C8` to the documents that define it, asserted by document
  path and by row CONTENT and never against a pinned line number, since these documents
  are edited weekly and a pinned line is an assertion that goes red for a reason nobody
  wants to fix and gets deleted instead. It finds **three** sites where §4's one-liner
  found two, because that pattern treats the hyphen as a namespace and §2.2 rules that
  it is not — `archivewrite`'s `C-8` is the third, and §1's ambiguous sentence *"C-8
  finished"* is the hyphenated spelling, so the extra hit is the fix rather than noise.
  Stdlib only, no vault, no socket, no client. 28 checks, floor 26 — section 4's two
  growth arms declare skips in the unreachable no-control-token case, per checks.py's
  mandatory-core guidance. ~1 s),
  `toolkit/test_citelint.py` (**`file.py:NNN` citations in study prose actually
  resolve.** Measured 2026-08-29 on `studies/movement/PROBE-GATEFIRE.md`: roughly 25 of
  its ~30 citations pointed at the wrong line — `fence_verdict` cited at `movetap.py:3049`
  and living at `:4691`, `INVALID_POS` cited at `:290` and living at `:512` — and **all
  eight `movesync.py` citations were stale UNDER A GREEN sha256 PIN**, because the pin
  says the file has not moved since it was taken and says nothing whatever about
  citations that were already wrong when it was taken. That is the whole lesson: a byte
  pin and a citation check are not the same instrument, and the document had the
  stronger-looking one. The citations were deliberately NOT swept at the time and that
  call was right — a sweep with no checker behind it buys a few days, and this repo has
  already paid once for the eager version (`test_provlint.py`: 46 citations rewritten,
  all 46 reverted the same day). So the checker came first and the sweep came second,
  in that order and in one commit. **The parse is the design.** Most citations name a
  SYMBOL beside the number, so the claim is machine-checkable; the pairing rule is a
  MEASURED gap bound (every true pairing in the pilot normalizes to ≤13 characters,
  every false one to ≥25, so the bar is 16) plus a refusal of sentence punctuation, and
  a pairing it cannot make degrades to a line-exists check that is COUNTED, never
  guessed at. Two rules were written only because running it over the corpus refuted the
  first draft: **hard-wrapped lines must be joined** — a same-line reader passes
  ```sep` is written at`` / ```movetap.py:791``` on line-exists and it is wrong, `sep` is at
  `:1120` — and **a hex literal is not a symbol**, since `0x0056` scans as the
  identifier `x0056` and opcode citations are everywhere in these documents. **TWO
  POSTURES, on purpose.** PROBE-GATEFIRE.md is RULED ON at zero red with no headroom
  (31 citations: 23 now resolve at the symbol tier, 7 at the line tier); every other
  `studies/**/*.md` is COUNTED at **142 red, ceiling 210** — the same ~1.5x headroom
  `test_provlint.py` used for 134→200 — because 142 is volatile by construction (one
  commit near the top of `agents.py` moves every citation of it at once) and a checker
  red on all of them is one nobody leaves switched on. **The 142 are not a fix list.**
  Section 7 is the red proof and it runs every time rather than being asserted: a
  scratch copy of the real document has ONE known-green citation moved by one line, and
  the run requires the verdict to flip, the report to name the document, the document
  line, the symbol AND the lines the symbol is really on, and the red count to rise by
  exactly one and not cascade. Section 5 is the vacuity guard the shape demands —
  three named citations pinned to their expected verdicts, two of which must come back
  `ok-symbol`, because a resolver that silently matched nothing would leave every
  "no red found" check in sections 6 and 8 green. The one historical exemption is
  checked in BOTH directions: C4's row cites `movesync.py:602-606` *in order to say the
  code is gone*, so fixing the number would assert the opposite of the row, and an
  exemption the scanner stops producing fails too. NOT covered, said so a green run is
  not over-read: only `studies/` — `CLAUDE.md`, `RUNBOOK.md`, `PLAN.md`, `HANDOFF.md`
  and this file carry citations and are outside it; fenced blocks are skipped as tool
  output rather than claims; and line numbers only, never whether the cited code says
  what the document claims. Stdlib only, no vault, no socket, no client. 50 checks,
  floor 50 — no optional section and no skip, so the floor is the whole run. ~3 s),
  `toolkit/test_derivlint.py` (the SECOND gate's checker, and it had never had one.
  `PLAN.md` §6.1 opens with `gwdat.py` landing as a port of an unlicensed repo the day
  after the plan forbade exactly that, and closes the paragraph "The rule was in the
  plan; nothing was checking" — `content.py` checks the row-level half, nothing looked
  at MODULES, and on 2026-08-17 Fournux/Tyria-Extractor turned up cited 100+ times
  across sixteen studies and five modules, supplying a rule `textrec.py`'s own
  docstring says was NOT re-derived, with no §6.1 row and no notice — MIT, so the
  missing notice was an unmet obligation rather than an untidy table. **The check is
  PER-UPSTREAM and the measurement is why**: 21 upstreams are named across `toolkit/`
  in 223 (module, upstream) pairs, and `gw-preservation/server` alone appears in 106
  modules precisely because it is the one we may not copy — so a per-pair rule is the
  permanently-red test that gets deleted, which §7 of `test_dispatch.py` documents at
  length. Fourteen upstreams, each accounted for by a §6.1 row, a notice, or a
  `NO_DERIVATION` row naming its site; both allowlist directions checked, stale and
  orphan. **Every sabotage runs against a SYNTHETIC repo root**, because a test that
  only asserts "the tree is clean today" passes equally well once the scanner stops
  finding anything — §2 plants a module, removes the row, and requires UNACCOUNTED,
  then shows the row clearing it while MIT still separately owes a notice. **§3 is the
  sharpest and is not hypothetical**: `PLAN.md:33` is the prior-art LANDSCAPE table,
  granting nothing, 1,030 lines above the register, and a recon lane read a Fournux
  mention there as a register row and recorded it as fact (`studies/quests/AUTHORING.md`
  §7 killed it). A `"Fournux" in open("PLAN.md").read()` check repeats that mistake and
  would have scored the tree CLEAN on the day the row was missing, so §3 builds that
  exact file and requires UNACCOUNTED. §4 proves the skip list is load-bearing — with
  `mirror_priorart.py` in scope the census inflates 14 → 21, since the fetch manifest
  names every mirror by construction. `audit()` takes `no_derivation` as a PARAMETER so
  the synthetic roots do not inherit the real allowlist; §2 pins that reading the module
  constant instead would make all three rows orphans and the orphan check meaningless.
  Floor 17 against a run of 20 — §5 adds one per allowlist row, and a tree where every
  upstream had earned a real row would legitimately run 17. No vault, no socket, no
  client),
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
  never called being the failure `test_atex.py` §3 names. Floor 21 = a whole green run;
  **this file has NO client-free core and going red without one is deliberate**,
  which was MEASURED on 2026-08-30 rather than assumed: `RURIK_VAULT` at an empty
  directory gives **0 checks, 1 declared skip ("everything"), rc=1**, and the
  reason printed is `checks.py`'s zero-checks rule, not the floor — no floor could
  make that run green, since `Ledger` refuses a floor below 1. §3 and §4 need no
  client but sit after `main()`'s early return, so they do not run either. Before
  that day the bare run gave rc=1 and NO verdict at all: `pinned.find()` raises
  `SystemExit`, which `except Exception` did not catch, so the skip was
  unreachable),
  `toolkit/mapdata/test_tilerender.py` (PLAN A3's atlas-tile renderer -- the step from
  "the client draws art we wrote" to "the compass draws OUR MAP". A picture is the
  easiest thing here to be confidently wrong about, because it looks like terrain
  either way, so the three decisions that fail silently each get a check that could go
  the other way. THE SIGN FLIP is asserted in BOTH directions: archive heights are
  NEGATED (greater stored = lower ground), and with the flip the rise side reads
  brighter by +48.7 luma while `negated=False` INVERTS it to -51.1 -- a one-directional
  check would pass on a renderer that ignored the flag entirely. PLACEMENT is derived,
  not assumed: the atlas coordinate is `local + footprint_origin`, so map 143's 64x64
  belongs at texel (448, 448) of tile (1, 0), and putting it at the tile's own corner
  would be off by 448 and read as the shading being broken; a render that would straddle
  two tiles is REFUSED rather than truncated. And THE GENERATOR IS THE ORACLE for whether
  it is our terrain at all -- `deploy.gen_plaza` puts a 61-degree cliff at `gx == mid`,
  and the heightfield's largest column step must land there, dominating the runner-up by
  more than 3x (8,748 against 488). That bound is a WINDOW rather than an equality and
  the reason is measured: a 3-tap central difference smears a step by one column either
  side. An earlier draft asserted the heightfield stepped at "exactly one" column, read
  off a top-4 printout; `gen_plaza` is a gradient on both sides of the plaza, so it is
  simply false, and it went red on its own terrain. The paste is contained to 4,096 of
  262,144 texels -- 1.56%, against A1 replacing the whole tile, which is what shrinks the
  collateral onto the five other maps sharing it -- and the built container round-trips
  through the ATEX reader at 10 levels with a worst channel delta of 1),
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
  client aimed live, and a run with no `--confirm`. §12 (2026-08-17) is the
  LAUNCH-BUILD guard: the exe must be the build the live service is actually
  serving, read from the owner's own auto-updating install rather than from any
  pin — a pin is what we last chose, the service serves what it shipped this
  morning. It refuses a stale build BEFORE the login because the failure is
  otherwise expensive and late: the updater is LIVE on every `run-live/` build by
  design, so a stale exe updates ITSELF and the key-tap cave — patched at a
  build-specific address — is gone in the copy that runs, spending the one
  authorized session on ciphertext with no key. Five checks and every one can go
  red: the matching build is ACCEPTED (the positive control), the stale one is
  refused naming both numbers, the refusal NAMES the staged directory that would
  work (and prints the rebuild command when none does), an absent owner install
  SKIPS loudly rather than passing, and an unreadable launch binary is refused
  outright. §13 (2026-08-17) is the KEY TIE-BREAK. Pairing a tapped keyring to a
  capture's connections is a search, and its criterion was `key_fits` — which reads
  TWO BYTES, the direction bit and a catalog-sized opcode. That is cheap to spell by
  accident: on capture `20260817T231139` two leftover keys each passed it on each of
  two leftover connections, a clean 2×2 ambiguity, and the driver refused — correctly,
  because picking would have written noise that reads like a capture. But the refusal
  cost the largest connection in the corpus (122 KB, an entire Isle of the Nameless
  walk, 426 creates). So a second question is asked when and only when the first does
  not separate: does the WHOLE s2c stream frame to its FINAL byte under this key? A
  wrong ARC4 key is wrong for every byte after the first message, and noise does not
  walk message-by-message onto an exact landing — measured on that capture, 100.0%
  against 0.01%. It only ever NARROWS: if the full-stream test leaves none or more
  than one, the refusal stands and says which question failed. Four checks, each able
  to redden: the right key frames completely (the positive control, without which the
  test could be vacuously false and still look like it works), a wrong key does not,
  the RIGHT key still fails on a stream truncated off a message boundary (that is the
  `consumed == len` half, which catches a gap-holed capture rather than a wrong key),
  and an empty stream is not "complete". §3 also now pins that `reassemble()` WRITES
  the recomputed report back into `manifest.json` (2026-08-18): it used to recompute the
  whole per-connection report, print it, and drop it, so a capture that gained connections
  on a re-run advertised the old refusal forever — `20260817T231139` reached 15/15 on disk
  while its manifest still read `decrypted: false` for the largest connection in the
  corpus, and a consumer trusting the manifest over the directory would skip a file that
  frames cleanly. Three checks: the report is rewritten, `report_from` records which
  writer produced it (absent = `run()`, never re-assembled), and every other manifest
  field survives untouched. 120 checks),
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
  six. Since 2026-08-22 the E5 instant also carries `[58, agent, 0]`
  (GV_SKILL_FINISHED) in the very next slot — the corpus position, 5 of 5,
  castmech 3c — and §2 pins both the send and the slot, while §2b pins the
  family boundary from both ends: an ATTACK skill's press (family forced via a
  stubbed `_is_attack_skill`, because a bare machine has no content rows)
  animates with property 50, CastAttackSkill — both live Power Shot presses,
  and all 39 adrenal 0x00D2s ride into a 50 — and its E5 borrows NOTHING from
  the spell family (no 58, no hold pulse) while sending the attack family's
  OWN `[46, agent, 0]` (ANIMREF-R6, since 2026-08-31: castmech's "neither 58
  nor 46, 0 of 2" was the bow artifact FINDINGS §3 refuted — 46 rides the
  melee execution batch 40/40 across the full live corpus, and it goes out
  even on a whiff because it closes the player's ACTION, not the hit). §2c
  pins the R6 batch from both arms: default — 46 leads, the damage lands IN
  the batch despite a swing landed the same instant (the windup was the
  interval; the old path's interval gate silently swallowed a mid-chain
  press), no attack_started and no melee_attack_finished ride along (40/40),
  E5 opens and E3 closes; and `--legacy-attack-finish` restores the pre-R6
  wire exactly, pinned DEFECT INCLUDED — no 46, and the mid-chain press
  deals nothing — so the movement-lock comparison (FINDINGS §11b/§13: a
  held W after a press traveled 0.0 u for 6 s against retail's move-within-
  0.25 s-of-E3 bound) stays one flag away. §2d pins ANIMREF-R8, the ON-BODY
  EFFECT VISUAL (properties 20/21) — the channel R4 decoded and refused to
  wire until the id space was read (FINDINGS §16 reads it: `+0x78` a visual
  on the caster, `+0x7c` one on the recipient, 2077 the client's own "none",
  656/658 corpus events predicted including the CHANNEL). What §2d checks is
  the half that is ours to get wrong: a caster-only skill (200) sends one
  property 21 and nothing at the target; a recipient visual at another body
  (312) rides property 20 as `[prop, RECIPIENT, CASTER, id]` — victim slot
  first, the order reading B settled when caster-first attributed *nothing*
  in the corpus; the SAME id moves to property 21 when the skill is self-cast
  (which is why one id shows on both channels in the corpus); a skill with no
  `skill_visual` row sends NOTHING rather than a substitute id — the
  condition R4's refusal named; and `--no-skill-visuals` turns the channel
  off. It SKIPS loudly without the content rows. The PROPERTY-8 ACTION HOLD (wired 2026-08-22 after
  the client-handler read, skillcast 16.2) is pinned through the same
  sections: `[8 → 1]` closes every immediate press burst with the `→ 0` half
  ELIDED when the flag was still 0 (the ranger's t=12.9508 shape,
  transition-only), the spell E5's instant ends with the `[8→0][8→1]` pulse
  (4 of 4 live), and the queued press and begin carry
  no property 8 at all, and the E3 batch does not toggle it either. That
  last clause went the OTHER way for half of 2026-09-01: ANIMREF-RE shipped
  an E3 release (`[8 → 0]` behind the E3, the caster-freed instant, 19 of 19
  unmoved corpus cycles — which also resolved castmech P10's "recorded, not
  resolved", since the older corpus's silent E3s were casts a movement
  instant had already released and transition-only elides a re-release). The
  operator scored the shipped pair "very floaty" and "warping" and it was
  REVERTED the same day (FINDINGS §29). The corpus fact is not withdrawn and
  neither is the flag: §2 still runs BOTH arms, the default (E3 alone, hold
  rides on) and `--e3-release`, because the arm has to be proven live before
  the next A/B — the run that convicted it convicted a PAIR, so neither half
  is individually cleared. Bare-machine floor 33, 35 with
  the vault. The section that earns the entry is the QUEUE LAW: skill 105's two
  cycles both exceed its 2.0 s activation by exactly the previous cast's
  remaining aftercast, so E4 fires at accept but the cast begins when the
  caster FREES — the naive press+activation model is refuted by +0.64 s and
  +0.57 s residuals in the corpus, and the test drives two back-to-back
  presses through exactly that schedule — and since 2026-08-22 through the
  DEFERRAL that rides it: the queued press sends E4 ALONE (both live queued
  presses carry nothing after their E4), and rewinding to the begin fires the
  first cast's E5+E3 with the queued cast's debit-then-animation right behind
  the E3, the order retail shows at both of 153's E3 instants; a cast that
  never begins never pays, which is the terminated cast's missing debit.
  Timing is tested by REWINDING the
  pending entries, never by sleeping; the zero-recharge inversion pins that
  E6 waits for its E3 because the corpus never shows them inverted; and the
  real-content section presses skill 153 and requires E5 to carry recharge 8,
  the value ArenaNet's own wire echoed — it SKIPS loudly on a machine with no
  vault overlay, where every other section still runs. **That sentence was
  false here and in the file's own docstring until 2026-08-31, and it is worth
  reading as a warning about this document rather than only as a fixed bug:
  both said "runs on a bare machine" and neither had ever been tried, so a
  vault-less run produced a TRACEBACK before check 1 — not a skip, not a floor
  shortfall, no verdict at all.** Three defects stacked. (1) `handle_skill_press`
  called `player_rank_for_skill`, the one lookup on the press path with no
  bare-machine fallback, so the SERVER — not the test — raised `ContentError`
  on skill 42 after having just logged `skill_timing`'s "falling back to 0" for
  that same row; the fallback now lives beside its four neighbours' and
  `test_bareimport.py` §3 executes a press with no vault to keep it there.
  (2) The press burst's 0x00A2 debit is `skill_cost`'s, a second content read
  the claim never accounted for; §§1, 2b and 4 stub it, as 2b already stubbed
  `_is_attack_skill`. (3) Both `LEDGER.skip` calls passed one argument to a
  two-argument signature, so the skip paths raised `TypeError` the first time
  they were ever reached — seven files across four packages had that same
  defect, all on branches only a resource-less machine takes, which is why the
  suite never saw one; `test_srclint.py` §10 now lints the arity tree-wide.
  Floor 24 → **31**, the MEASURED bare-machine subset, against a green 33 with
  the vault (§5's two checks are the difference) — the shape `test_armour.py`
  and `test_position_trust.py` use),
  `toolkit/authsrv/test_pressscore.py` (the instrument ANIMREF-RE §36's rule
  needs — "measure the symptom on the wire in their post-fix capture before
  writing the word fixed" — checked before a number it prints is trusted.
  `pressscore.py` finds every c2s 0x0026 press in a gamesrv capture, names its
  last movement input, whether an attack_started answered it, and — by
  replaying begin_attack / cancel_on_move / _player_body_moving / attack_tick
  at the capture's own tick instants — which gate refused every unanswered
  tick; then forks the state at each press to score the click-latch bounds
  against each other in both directions. §1 is BARE: a synthetic capture (one
  click, one press, the ticks, the wire's own swing) checks the last-input
  classifier, the leg model's arithmetic, that the constant bound opens at
  click + 3.0 s while the leg bound opens on the first tick after the leg
  ends, that "the press ends the leg" opens while the modelled body is still
  walking and is flagged as the bad arm, and that a capture stamped with the
  leg flag whose wire carries a constant-bound swing FAILS the replay control
  and says so — the tool refusing to score a capture its rules did not
  produce. §2 re-runs the §36 headline on the three 2026-09-01 captures and
  requires the replay control to close on each (52/52, 23/23, 11/11 starts),
  declared skip without them. Floor 14, the bare half, measured both ways —
  20 with the vault, 14 with `RURIK_VAULT` pointed at an empty directory),
  `toolkit/authsrv/test_playerswing.py` (the player's auto swing is TWO
  phases — ATTACK_STARTED, then the damage `swing_windup(ATTACK_INTERVAL)`
  later — where until 2026-08-22 it was one instant, the last attacker in the
  file with no mid-animation window (studies/combat 17e item 1; the windup
  constant's three independent legs are studies/castmech M1). §1 pins the
  split: the first tick sends the START with the `[8 → 1]` action hold riding
  behind it (4 of 4 live, castmech 3c), the landing a windup later is
  gain/damage/FINISHED with NO second START and no hold toggle — the chain
  still holds. §2 pins the gate as
  START-to-START — right after a landing nothing fires, because the backswing
  half of the interval is a wait with no wire event, and the next START opens
  one interval after the previous one. §3 drops an armed swing whose target
  died, left reach, or whose owner died — silently, ArenaNet's own truncation
  shape (the Lakeside 7th swing, cut 0.24 s in, no closing event), except that
  a DEAD target also releases the hold on the wire (t=20.1637, n=1) where
  out-of-range, unwitnessed, stays fully silent. §4 is the
  regression guard for the other callers: a default `hit_enemy` call still
  opens with its own STARTED, lands in one instant, and respects the interval
  gate — the attack-skill path's recorded divergence, deliberately unchanged.
  §5–§7 are the cancel half: a skill press puts `[8 → 0]` then
  GV_ATTACK_STOPPED [3, agent,
  0] immediately after E4 — retail's own burst order, the release preceding
  the stop, 2 of 2 live presses with
  a chain running — drops the armed swing through the tick-owned flag, keeps
  the TARGET (retail resumes the chain), and stays silent when the chain is
  already paused (the necro's press 2 carries no STOPPED); the chain pauses
  while any pending cast is short of its E3 and the next swing opens on the
  first tick after it — ATTACK_STARTED rides the E3 instant on both live 105
  cycles; and a retarget stops the swing in flight with the corpus's
  standalone-stop shape (17c, n=1 — now pinned as the full `[8→0][3,agent,0]`
  pair) and opens on the new target the same tick.
  Timing by rewinding the armed swing and the start gate, never by sleeping.
  **§5, added 2026-09-01, is ANIMREF-RE §31's chain pause, and it is scored on
  RETAIL'S OWN METRIC rather than on a threshold somebody picked**: retail's
  attack-started gaps are a metronome when the player stands still (n=816, p50
  1.330 s, p10 1.318, p90 1.345) and stretch to 2.007 s when a move falls inside
  (n=40) — ratio 1.51 — while ours scored **1.003**, a chain that never noticed
  the player walking. The section drives the REAL `attack_tick` on a stubbed
  clock through 240 ticks with a 1.5 s moving span and requires: the legacy arm
  to score ~1.0, the shipped arm to stretch, the two to SEPARATE, and the
  residual `gap − moving_span` to land back on the metronome — the corpus's own
  signature for a pause rather than a re-stamp (retail 10/40 in band, while
  `next − last_move` is 0/40). **The known-bad arm scores exactly 1.000, which
  is the only thing that makes this a metric and not a formality.** That
  residual check earned its keep immediately: the first implementation
  accumulated the freeze BELOW the landing branch and silently skipped whatever
  part of the moving span overlapped an in-flight swing's windup; the ratio
  still looked fine and only the residual went red. Floor 24 → 30, and §5 is
  fixture-free so 30 is the bare-machine number too. **§6 (ANIMREF-RE §33/§35)**
  pins all three arms of the auto-swing hold — shipped (no property-8 hold at
  all), revert+F1 (held, released at the landing) and both-legacy (held, never
  released) — plus a check that a CAST still holds. **§7 (§34)** pins the
  click-walk latch from both sides: a fresh click reads as moving, a stale one
  does not, an ordered attack after a finished click-walk opens a swing end to
  end, and the known-bad arm — a swing ordered during a live click leg — still
  waits. **§8 (§37)** replaces §7's borrowed 3.0 s constant with the leg's own
  travel time and pins BOTH failures of the constant: a 1.0 s leg reads parked
  at 1.5 s (the operator's 60.6 % deficit as one assertion) and a 5.0 s leg
  still reads moving at 3.5 s (a swing on a walking body); the leg starts from
  the previous leg's interpolation when the client has been silent since it,
  from the report otherwise, runs at the DECLARED base (Rush's 360 u/s), is
  matched to its latch by stamp identity rather than age, and the revert arm
  `--click-latch-window` restores the constant exactly. End to end, a press
  0.5 s after a 0.3 s click opens on the first tick where the constant held it
  2.5 s, and the known-bad arm — a press 0.5 s into a 1.0 s leg — still waits.
  **§9 (§38)** is the reach and the approach, 27 checks with `ATTACK_APPROACH`
  forced on and restored: the constants and their provenance (`BOUNDING_RADIUS`
  unpacked from the `0x41400000` every `0x0020` carries, the follow stop
  `r + r + 56 = 80` from the client's def pad, `ATTACK_REACH = 144` inside both
  DR-free retail brackets, the flag-off arm still 1500); then the real
  `attack_tick`: in reach opens at once with no follow, 400 u out sends the
  retail-shaped `0x002A [player, target's own point, plane, plane, target]`
  and arms latch + leg to the stop point and `dest` with no swing, no re-path
  on a standing target, one re-path to a moved target on the 0.5 s tick and
  none inside it, arrival opens the swing and forgets the follow with no
  `0x0028`, a report abandons the follow and the next tick re-follows, a
  retarget re-follows the new target, the snap guard puts a `0x002C` at the
  modelled click-leg end before the follow when the copy is 500 u off and none
  at 60 u, a leftover follow naming another target is abandoned, and source
  pins count the six `_approach_abandon` call sites (minus the `def` — the
  substring trap, caught on the first run).
  **§10 (§39)** is the operator's CASE 6 verdict as 14 checks: a press 1.0 s into
  a click leg clears the latch and its record, re-pins the body once at the
  modelled point (`0x002C`), and the next tick swings (target in reach) or
  follows from the re-pinned point (out of reach); `--press-waits-for-leg` leaves
  the leg alone; a repeat press on our own follow's target is left alone; a
  parked body gets no re-pin; a post-landing move forgets the target with no
  close and the chain does NOT resume over three ticks (retail's player
  re-presses, 28/28); a pre-landing move still sends the stop pair; a move ends
  the follow; `--move-keeps-target` restores §32's keep; the press arm calls the
  supersede before `begin_attack`. §3 now runs the no-approach arm (retail
  auto-chases a target that walks out, §9's territory).
  **§11 (§41)** is the operator's "couldn't resume attacking" as 20 checks, after
  the capture REFUTED the click-latch reading (every press ends the click latch;
  the starve began at the session's first `0x003D`, whose `0x0047` never came,
  and `_player_body_moving` read the keyboard latch unbounded): the reader both
  ways (a keyboard latch older than the press no longer moves the body; a newer
  or equal one does; no press at all leaves the raw latch, so rule 1 and the
  cast-stop are unchanged), the 24.44 s press end to end (latch 0.29 s old, no
  stop, target 86 u → swing on the first tick, row `swing`), the known-bad arm
  `--press-waits-for-stop` (waits; ONE `moving` row naming latch `kbd` and its
  age across three ticks; then the stop releases it and the answer row carries
  `refused_by: moving, ticks: 3`), a move between press and tick
  (`move-ended-order`, terminal), a REFUSED click NOT starving a press inside
  reach — with the arm's stamp-before-verdict order pinned as intended, since the
  client walks a refused click — the `repeat` / `no-target` / `dead-target` /
  `follow` / `interval` rows, rec=None still resolving the press, and source pins
  on the three recorder hand-overs, the stamp's one writer and one reader, and
  `kbd_moving_at`'s unchanged two writers (by AST, not by text — a docstring
  quotes the arm). §7's "the client sends the stop 36 of 36" is rewritten with
  its refutation; §10j's call-site pin now names the recorder argument.
  Floor 42 → 55 → 82 → 96 → 116; §6–§11 are fixture-free so 116 is the bare-machine number),
  `toolkit/authsrv/test_castcancel.py` (movement cancels the cast, and the
  contract is the wiki's expressed as wire SILENCE: the connection thread
  MARKS (`cancel_on_move`) and sends only the movement's own `[8 → 0]` hold
  release (4 of 4 movement instants in the corpus — during aftercast too,
  where retail's client refuses the input and the general rule inherits),
  the tick releases with the bare `0x00E2`
  [agent, skill, copy] — the corpus's own terminated-cast shape, E4 t=5.027
  answered at t=5.912 with no E5 between or ever after — and then §1's
  60-second rewind proves no E5/E3/E6 ever follows: no recharge started, no
  aftercast served, costs staying paid for any cast that BEGAN (a queued cast
  dropped before its begin never paid, which is that same terminated cast's
  missing debit — castmech 3c). §2 pins
  the boundary: past its E5 a cast is aftercast and is NOT marked — E3 and E6
  close normally. §3 is the wiki's attack-skill asymmetry: mid-activation an
  attack skill shrugs movement off, but one still QUEUED (its begin never
  reached) drops whatever its type — a spell activating and an attack skill
  queued behind it both release, two E2s, no recharge for either. §4 proves
  the busy-window rollback: a press after a cancel schedules its E5 one
  activation out, not behind the cancelled cast's ghost. §5 is the chain
  half, both doors — and since ANIMREF-RE §31 LAW A is the DEFAULT again,
  **composed with the chain pause as one arm** (`--legacy-move-stops-chain`
  reverts both, because they are meaningless apart: with the chain closed on
  every move there is no chain to pace). The half that was missing turned out
  not to be a movement gate at all — the client refuses a walk cycle by
  ANIMATION PRIORITY while an attack animation is latched (table `0x00A92ED8`,
  locomotion `0x0040` against `0x0110`/`0x0120`), and retail sends no
  pose-ender: it stretches the chain so the animation finishes. The section
  pins both arms and the fact that the `[8 → 0]` release rides on both. The
  paragraph below is the history that got here — LAW A alone shipped for half
  of 2026-09-01 and the operator scored the §28 pair
  "very floaty" and "warping", so the prop-3 door is default once more —
  now on a FEEL verdict rather than the old tap-train reading, which the
  §28 decode had already dismantled (the "unidentified grant" retail feeds
  a mid-chain mover is the client's own 250 ms resume poll, prop 8's
  gate-clear at 0x0081C090, and the tap-train freeze was retail-consistent
  tap behaviour since the resume rescues held keys only). Both arms still
  run, and the LAW-A arm came back RICHER than it left: besides the absence
  of the prop-3 it now pins the **walk-gate re-hold** — with the chain
  surviving the move, `attack_tick` re-sends `[8 → 1]` one tick later on a
  body that just walked, setting the gate against the movement door's own
  clear. That toggle is FINDINGS §29's leading suspect for "floaty" and it
  shipped unmeasured; the check exists so it cannot go unnoticed twice. The
  section also pins what the revert does NOT touch: the `[8 → 0]` hold
  release rides on both arms — it is the one piece of the door they share,
  and it is what arms the client's resume poll. Floor 24. §6 is the
  `0x0028` CANCEL_ACTION door, the arm the first operator run forced: the
  client sends NO movement c2s while it holds a cast — the operator's three
  cancel inputs each arrived as a header-only 0x0028 (run 20260823T101329),
  so the movement door alone left casts uncancellable on screen. The section
  pins the grant: the request marks the cast and releases the hold ([8→0],
  the E2 staying the tick's), reaches the mid-activation attack skill that
  movement spares (the client withholds Esc for skills that resist it, so an
  arrived request is granted), leaves an aftercast holding and unmarked
  through this door too, and closes a live chain with the [8→0]-then-STOPPED
  pair while forgetting the attack order — Esc means stop, not pause.
  **Re-pinned 2026-08-24 to the live cancel-family capture**
  (`20260824T074002`, sealed plan, both connections framed to the last byte):
  the release burst is `[8→0, 59, E2]` in one instant, 4 of 4 cancelled casts
  — property 59 is what stops the BODY, which is why a cancelled cast used to
  keep animating — and the swing pair is `[3, 8→0]`, the opposite of the
  press and retarget orders, each door keeping the order measured at it.
  The tick now only removes a released entry; §1 asserts it announces nothing
  a second time. Floor **21** — this entry and the file's own header comment
  both read 20 while the code said 21; the code was right and the run agrees.
  NO VAULT, NO SOCKET, NO CLIENT: every section stubs `skill_timing` and
  asserts on the cancel wire, which carries no content-derived value, so the
  count is 21 with a vault and 21 without (MEASURED both ways 2026-08-31).
  That property is one day old rather than original — until then a bare run
  died in `handle_skill_press` on the same unguarded `player_rank_for_skill`
  read that killed `test_castcycle.py`, with the difference that THIS file
  never claimed a bare machine in prose. Both were equally broken, so an
  unstated dependency is not a safer one, only a quieter one),
  `toolkit/authsrv/test_animgrammar.py` (the ANIMREF episode machines on
  synthetic streams they cannot force — bare-machine, no vault. The corpus
  run itself is guarded by `animgrammar.py --control` (P-CTRL: castgaps'
  seven cycles, the 0.74–0.77 s aftercast gaps and the Power Shot windup
  gaps reproduce to 0.1 ms), so THIS file proves mechanics: `prop_events`'
  normalisation of all four property channels including 0x00A3's
  victim-first slot order (the trap adrenjoin.py documents), the 0x0035
  (base, modifier) declaration, signature tokens keeping the
  targeted/untargeted cast-channel distinction (ANIMREF-Q1's observable),
  the ADRENALINE FAMILY added by ANIMREF-R9 (0x00CF gain / 0x00D0 clear /
  0x00D1 set / 0x00D2 spend decode into one event shape where the absent
  fields stay **None**, never 0 — a gain names no skill and a spend no
  units, and a zero would read as a measurement never taken) **together
  with the regression that matters**: an adrenaline event sharing a batch
  does NOT enter the episode signature by default, because letting it in
  would silently rewrite every published one (FINDINGS §3's
  `['E5','46','dmg','E3']`) and every count in §3 and §8 — a new instrument
  must not invalidate the measurements taken with the old one, so the
  opt-in (`SIGN_ADRENALINE`) is explicit and pinned OFF,
  the swing state machine (landed with SOURCE-slot damage pairing, stopped,
  reopened, censored, ratio None without a declared speed), the self cast
  machine opening on E4 so the queued-terminated family (E4→E2, no
  animation property ever) survives extraction, batch signatures in stream
  order, the `[8:0, 59, E2]` cancel burst, no E-tag reaching back before
  its episode's open, interleaved skills keying independent episodes, the
  other-agent machine (60/50 opens, 58 finish, 59 cancel, reopen, censor,
  timeout sweep), 0x00F1 recorded as a mark and never a close, and the
  property census keeping unknown ids; the batch clustering (eps=0 exact for live tapes, 5 ms for gamesrv logs whose sends stamp their own clocks); and scan_ours itself over a synthetic RURIK_VAULT -- hand-packed 0x009F rows the codec must frame, the tape-replay exclusion by label, and the era filter that makes the pre-castmech known-bad control possible. Floor 41),
  `toolkit/authsrv/test_cancelwalk.py` (**2026-09-07: its halt-site finder now accepts the
  `_send` wrapper `_npc_follow_tick` has used since NPCTRACK-Q1 (fb492bf); the two
  site-count locks had been red on main from that commit until then.** Everything AROUND the
  CANCELWALK
  runs — the walk-on-cancel experiment arms of `--cancel-answer`
  (`studies/movement/CANCELWALK.md` §5), whose verdicts are operator runs and
  deliberately not this file's. §1: `parse_cancel_answer` accepts exactly
  `suppress`/`retail-lead`/`lead:<u>` and refuses everything else LOUDLY,
  typos included — a mistyped experiment must not run the shipped default
  under an experiment's name. §2 is the file's spine: `cancelwalk_lead_dest`
  reproduces retail's own three cancel-instant granted points from the live
  capture's reported+vec2 within 0.02 u (the D1 formula, `20260824T074002`
  t=81.660/114.641/128.805), measures a fixed lead along the UNIT heading,
  and grants the reported point on a degenerate one. §3: the composition
  matrix refuses the arm without `--zero-lead` (the inert-flag defect) and
  with `--arrival-carry` (the F1b queue would model the reported point while
  the wire carried the led one), and notes the allowed combination as
  DIAGNOSTIC ONLY. §4: `cancel_on_move` returns what the press hit —
  `cast`/`swing`/None, once per entry — which is the return the 0x003D arm
  keys the changed answer on. §5 greps the handler for the gates a run
  depends on: the 0x0025 send and the walking latch both guarded on NOT
  cw_suppress, ONE 0x0029 send site serving default and lead arms alike, and
  the hit captured from the return value rather than a state latch the click
  arm would leak through. **Extended same day for R4's `,stop` modifier**
  (the runs landed within hours: R1 froze, R2/R3 walked the granted leg to
  the point exactly — CANCELWALK.md §5a): the modifier parses on both lead
  forms and is REFUSED on suppress (no leg to stop), and §5 gains the leg-
  window source locks — cleared on every grant, re-armed only at a
  `,stop` lead send sized to the leg at 288 u/s, and the stop-arm answer
  guarded on CANCEL_STOP AND the live window, which is what keeps it from
  being the refuted --stop-echo under a new name. **Extended 2026-08-24 for
  R6's `--stop-answer`** (the state-diff round's H6 test, CANCELWALK.md
  §7.4): §6 drives `parse_stop_answer` (`ack` in, `repin` REFUSED as
  deliberately unbuilt — the refusal itself carries the licensing decision,
  naming --stop-echo's wire effect — and typos refused naming the real arm),
  the two new composition refusals (no `--zero-lead`: the run answers an
  unregistered question; with `--cancel-answer`: two levers, attributable to
  neither), the allowed-with-note combination, the constant TIED TO THE
  SCHEMA (overrides.json GAME_SMSG "40" must still name AGENT_STOP_MOVING at
  high confidence, or the arm's mechanism story moved and the check goes
  red), the exact wire shape round-tripped through the real codec (6 bytes,
  `[0x0028, player]`, zero residual — "a wrong ANSWER SHAPE from the server
  would be this file's"), and the source locks: the R6 send site gated on
  STOP_ANSWER, default None, main() routing the parsed MODE into the
  composition matrix so the refusals cannot be dead letters. **Extended
  2026-08-24 for R8's `--cast-stop`** (the F28 float-forward fix wired at
  the cast start, CANCELWALK.md §8): §7 drives the four new composition
  cells (no `--zero-lead`; with `--cancel-answer`; with `--stop-answer` —
  the SAME opcode on two triggers gets its own cell naming it; with
  `--arrival-carry` — the halt cuts short a leg the F1b queue modelled as
  arriving), the pairwise-before-requires precedence (BOTH ways for the
  arrival cell: the adversarial pass caught it placed below
  arrival-requires-zero-lead, where its refusal handed out advice the
  pairwise cell then refused), the allowed-with-note combination, and then
  the burst DRIVEN rather than grepped: `handle_skill_press` with the flag
  off (no 0x0028 — no diagnostic ships on), on (exactly one 0x0028
  `[player]`, the builder's payload, riding first in the cast-begin TAIL —
  before the animation, which precedes the prop-8 hold; the E4 and the
  debits legitimately precede it), and on with an attack skill (the burst
  goes out, proven by its own animation, and carries no 0x0028 — the halt
  is scoped to NON-ATTACK casts). Source locks: one gate carrying the
  scoping, one R8-labelled site, default off, main() routing the flag
  into matrix and global with the arming assignment itself pinned
  (deleted, the flag would print a full banner and send NOTHING, an
  inert arm on a readout the wire cannot see; §6 gained the same pin for
  R6's `STOP_ANSWER = _sa_mode`). A 6-mutation probe (payload literal,
  scoping deleted, order swap, refusal cell deleted, default flipped,
  flag unrouted) went 6 of 6 RED. **Extended 2026-08-25 for R10's
  `--cast-stop=pin`** (the no-warp successor after the owner refused the
  bare halt — F31 warps — PLAN §7 Q10): §7 now also drives
  `parse_cast_stop` (halt/pin in, typos refused naming both arms AND the
  ruling), `cast_stop_reckon` as a pure function — the straight-leg
  arithmetic exactly (1.5 s at 288 = 432 u), the rate table, and every
  refusal door: `parked`, `no-report`, `report-refused`
  (`_resync_verdict`'s refused-report hole, guarded here too),
  `pinned-parked` (the R8 second-cast trap) with its
  report-newer-than-pin reopen, `future-report`, plus the navmesh clip
  (`reckoned:clipped`) via a fake pathmap — then the pin BURST driven
  with seeded motion state: one 0x002C `[player, reckoned point, plane]`
  BEFORE the 0x0028, the 0x0028's label carrying the reckon verdict (the
  refusal telemetry IS the label), the `cast_stop_pin` state note
  landing, the second-cast guard refusing a second 0x002C live, the
  parked belief sending none, and an attack skill under pin with a
  moving belief seeded sending neither message. New lattice cells:
  pin×`--resync` refused naming the shared 0x002C (halt×resync still
  composes, its note now carrying the ruling), both modes through the
  shared cells. Source locks: one 0x002C site (`CAST-STOP PIN`), default
  None, the parsed MODE routed. **Extended 2026-08-25 again for the
  §8.3a review fixes** (two BLOCKERs — both warps, both failing PLAN §7
  Q10's bar — and three REALs, from the adversarial pass over the wired
  pin): §7's reckon drive now asserts B1's `click-walk` door — a click
  in flight refuses AND outranks `no-report`, because it is the one
  label the send site suppresses the whole cast-stop on (the 0x0028
  alone on a silently-pathing body warps onto a sync copy parked at the
  click leg's start, corpus p50 1,164 u) — with the BURST driven both
  arms under a click seed (no 0x0028, no 0x002C, the animation proving
  the press was not refused) and source locks pinning the latch's
  wiring (armed once in the 0x003E arm, cleared twice — 0x003D and
  0x0047 — consulted at the send site before EITHER arm); B2's census
  family rates ({1,2,3} 1.0 and {4,5,6} 0.652 driven per-mt, both
  OBSERVED; {7,8} 0.75 LABELLED, the weak row; mt 9 refused
  `unverified-rate` — the old mt-4-alone 0.66 table hard-set a strafing
  cast forward past the registered 35 u bar); R1's plane resolved AT the
  extrapolated point (`plane_at(est, prefer=report)` — a fake pathmap
  answering 5 against a report saying 12 proves the report never rides
  the wire — and `no-plane` refusing where the geometry cannot say);
  R2's off-mesh REFUSAL (the check that used to assert the
  standing-outside suspension now asserts its opposite — a wire hard-set
  gets no suspension, `off-mesh`/`no-mesh` refuse rather than ship a raw
  ray); and R3's model park (a SENT pin drops `state["dest"]` and
  hard-sets `state["pos"]` to the 0x002C's own point, driven, so the
  20 Hz tick stops walking a phantom). **Extended once more the same
  day for the re-run review's yield** (13-of-13 mutation catch, no
  blocker; CANCELWALK.md §8.3b's re-review block): the R1 plane proof
  moved to the WIRE — a burst seeded report-plane 12 against a mesh
  answering 5 asserts the sent 0x002C's plane field is 5, closing the
  gap where every burst seed had plane 0 and a prefer-echoing mesh so a
  payload mutation stayed green; `zero_lead_composition(cast_stop=True)`
  — the legacy bool that armed every shared refusal cell while matching
  neither mode — is asserted to raise a loud ValueError naming both real
  arms; and the second-cast seed reads the pin note with `.get` so the
  M7 mutation (note never written) fails as a named check instead of
  aborting the section on a KeyError. **Extended a third time the same
  day for F34's pin-or-nothing fix** (R10's owner run measured the bare
  refusal-path 0x0028 warping a genuinely PARKED body 167.6 u backward
  onto a still-converging sync copy — CANCELWALK.md §8.3d — so the pin
  pair now fires whole or not at all): the burst driver captures the
  gamesrv console (the refusal label rides the print now, not a
  0x0028, so a test that cannot see stdout cannot protect the
  telemetry), the parked and pinned-parked casts are driven to WIRE
  SILENCE with their `pin:parked`/`pin:pinned-parked` labels asserted
  on the console line and the cast's own animation proving the press
  survived, the click-walk checks gain the same console assertion, and
  a source lock pins the `_cs_send_stop` gate's three sites — armed
  once, disarmed once (the refusal branch), consulted once — because
  with the gate deleted the bare 0x0028 returns and F34's warp with
  it. **Extended 2026-08-25 evening for the §8.3g SHIP ruling** (“pin
  it” — pin becomes the shipped default, wired zero-lead-style): §7
  drives `resolve_cast_stop_default` cell by cell — bare startup →
  pin/'default'; `--no-cast-stop` → off; under `--no-zero-lead` the
  default follows the regime it modifies instead of stranding on the
  requires-refusal; each of the four explicit experiment levers makes
  the DEFAULT yield with a `lever:<flag>` provenance (while the
  matrix still refuses the EXPLICIT pair — both halves pinned); an
  explicit mode passes through untouched; `--no-cast-stop` plus an
  explicit `--cast-stop` refuses as a contradiction; and the default
  never resolves to halt (the control is explicit-only, REFUSED as a
  ship). Source locks: the resolver called once in main(),
  `--no-cast-stop` registered, the default-on banner keyed on the
  resolver's own provenance. **Extended 2026-08-25 for the
  `--resync-separation` lever** (P8 of
  `studies/movement/followon-notes/p5-resync-disarm.md` §8 — the
  raised-threshold negative control staged for the `--resync` disarm
  run): refused without `--resync` naming its base flag and its
  registered use, refused non-positive AND non-finite (0.0, -100,
  nan, inf — a zero threshold is an unregistered 2 Hz 0x002C stream,
  a nan one an inert flag with an on-looking log), allowed with
  `--resync` with the note naming the OVERRIDE and the P8 protocol so
  the run log cannot claim the shipped cell, the pin×resync
  pairwise cell asserted to outrank the modifier, and -- after the
  review's mutation pass showed the main() rebind unpinned -- the
  `RESYNC_SEPARATION = a.resync_separation` assignment source-locked
  by name, CAST_STOP-style. **Re-aimed 2026-09-03: the 0x0028 source
  lock counted SEND SITES, and ANIMREF-RE §40 legitimately reddened
  it.** The old single check asserted "exactly TWO 0x0028 send sites";
  §40 landed a third -- retail's own NPC chase halt
  (`studies/animref/FINDINGS.md` §40.2: a bare `0x0028
  AGENT_STOP_MOVING [npc]`, **5/7** chases, p50 0.496 s after the last
  follow) in `_npc_follow_tick._halt`, gated on `NPC_FOLLOW`. A site
  count cannot tell WHO a halt names, so it could not distinguish that
  from the hazard it existed to catch: 0x0028 halts BOTH client copies
  where they stand. Re-aimed onto the invariant that carries the risk
  and split into four AST-based locks (`stop_moving_sites()` walks the
  calls and reports `(line, def-chain, builder, agent-expression)`):
  the R6 gate/label pair; THREE sites, every payload from
  `agents.agent_stop_moving` (never a hand-built `[agent]` literal,
  which would skip that builder's agent-id-0 refusal); exactly **TWO
  naming `PLAYER_AGENT_ID`**, in `handle` (R6 stop-ack) and
  `handle_skill_press` (R8/R10 cast-stop) -- the count carrying the
  safety argument, since `studies/movement/FINDINGS.md` §3.2's "a
  server author must not send `0x0028` on a stop" is scoped to the
  PLAYER's own stop window (0x0028 in 7 of 114 stops) and **187 of
  retail's 282 corpus-wide 0x0028s name a non-player agent** (95 are
  player-directed); and the third asserted to name `agent_id` inside
  `_npc_follow_tick._halt` behind `NPC_FOLLOW`, its INSTANT being the
  audited part (§40.9 moved it onto the follow's own half-second clock,
  `HALT_ON_CLOCK`, which §40.11 re-affirmed as retail-measured after
  retiring §40.9's own justification). A 5-mutation probe went 5 of 5
  RED with the exact locks predicted: a fourth site naming the player,
  the npc site re-aimed at the player, a hand-built npc payload, the
  `NPC_FOLLOW` gate removed, and the R6 send deleted under a standing
  gate. Floor 124),
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
  message, since two would draw two numbers on screen for one hit.
  **§§8–10 are the three directions added 2026-08-20, and each one existed
  because a client run showed the old behaviour was wrong.**
  **§8, HEALING** — the direction this server never had. Which property carries
  it was measured, not chosen: on `0x00A3` the live corpus has property 16
  negative **1251 of 1251** and 17 negative **243 of 243**, both self-directed
  **0 of 1501** (damage always has a distinct attacker and victim); property 55
  is **POSITIVE 502 of 506** and **SELF-DIRECTED 454 of 506**. A positive,
  mostly self-inflicted health delta on the damage channel is a heal, so GWCA's
  `armor_ignoring` names the mechanism and not the direction. The section pins
  that the heal goes out self-directed and positive, that an 88 heal on a 40/100
  bar lands **60 CLAMPED** (the `fraction <= 1.0f` assert only fires in the
  positive direction, and this is the first thing this server sends that can
  reach it), and that a heal on a full bar sends **nothing** — overheal is
  silent in retail too. Control: Power Attack heals nothing.
  **§9, A SPELL IS NOT A SWING.** Both halves were wrong until a run showed
  them: casting Faintheartedness, a HEX, produced `attack_started: player swings
  at 10` and 5 points of hammer damage, and Flare — whose own 20 fire damage was
  decoded and sitting there — dealt the same 5, because `cast_tick` read only
  the `additive` mode and dropped `standalone`. Now the TYPE column dispatches:
  only `type_code` 14 rides a weapon swing, `exact=` deals the skill's own
  number with no roll or armour or critical, and `swing=False` suppresses
  `attack_started`/`melee_attack_finished` — pinned as ONE message going out.
  **§10, CONDITIONS** — the join `studies/isle` asked for. It had established
  that a condition's duration comes from the INFLICTING skill (Burning's own
  endpoints are 3/3 and retail sends it at 9.0); what was missing was which
  condition and from where. Both are per-skill data already carried: **GWW's
  progression variable NAMES it** (`Sever Artery` has exactly one variable and
  it is called `Bleeding`) and **the client's bonus slot carries the seconds**
  (5..25, with `skill_arguments = 4` naming that slot — the bitfield picked it
  before the wiki was read). Sever Artery resolves to Bleeding 478 for 9 s at
  Swordsmanship 3, the apply names the CONDITION's id rather than the skill's,
  and the controls are the two that a label-blind reading gets wrong:
  `Health degeneration` is a real variable in a live bonus slot and is not a
  condition, and an attack with no bonus slot inflicts nothing. Floor 25 → 40),
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
  check.

  **The poison MOVED on 2026-08-20 and that is the interesting part.** The
  player's swing stopped reading `HIT_FRACTION` and started reading the
  weapon's own damage range, so the section went on poisoning a constant the
  code no longer consults — and passed, on a tree where the guard was never
  reached at all. That is precisely the failure this file exists to catch,
  scored against itself: **a guard test pointed at the wrong symbol is a guard
  test that cannot fail.** It now poisons `PLAYER_SWING_DAMAGE`, and the
  in-range control asserts a RANGE rather than an equality, because the roll
  inside the weapon's range is random and pinning it to one number would be
  pinning our own roll instead of ArenaNet's range. Every section carries an in-range CONTROL asserting the real
  constant still sends the full effect burst, because a guard that refuses
  everything would pass every refusal check. Dormant while every fraction is
  a literal constant; load-bearing the day studies/combat step 8 computes
  them from the client's skill table.
  **§2's fixture skill changed from a made-up 42 to Power Attack 322 on
  2026-08-20**, and the reason is the shape of a test quietly dying: the cast
  path now dispatches on the skill's TYPE, so an id that is not an attack
  resolves to nothing and this section's actual subject — that the damage lands
  at E5 rather than at the press — would have stopped being tested while still
  printing PASS. A CONTROL was added beside it that could not have existed
  before the fix: casting a HEX at the same agent must swing nothing at it.
  **The four in-range CONTROLS were re-pinned on 2026-08-21** when the adrenaline
  family went on the wire: the counts went 3 → 4, 2 → 3, 1 → 2 and 6 → 7, and each
  one now names the trailing `0x00CF` explicitly rather than absorbing it into a
  bare literal. Two of them carry a claim worth more than the count — the swing's
  `MELEE_ATTACK_FINISHED`-then-damage adjacency is ArenaNet's own (6 of 6 in the
  Lakeside tape) and the adrenaline message is APPENDED after it, never inserted
  into it; and the overkill row's 7 is what would catch a later session sending an
  adrenaline message for the dying AGENT, which retail never does (self-scoped,
  9 of 9). Floor 40 → 41),
  `toolkit/authsrv/test_morale.py` (morale and the death penalty — the
  arithmetic, the gate and the wire tick. Three things are actually at risk and
  each has its own section. **The base-versus-total scale**: morale scales a
  character's BASE health and energy, never the totals, and on the one death
  ArenaNet's corpus contains that is the difference between the observed 22 and
  the naive 21.25 — so §1 pins the ENERGY figure (the discriminating one; health
  cannot discriminate, because base and total are both 100 for the character we
  ship) and asserts outright that scaling the total does NOT reach the observed
  number. **The gate**: every map this server ships is pre-Searing, where retail
  charges nothing for dying (GWW, "Death Penalty", Exceptions), so §4 asserts
  the SILENCE — a death in Lakeside County puts no morale on the wire — and then
  asserts `--death-penalty` breaks it, because a default that fired would look
  like a working feature and be a fabrication. **The revive**: the penalty lives
  entirely in the maxima, so the cheapest way to delete the mechanic is to
  restore `PLAYER_HEALTH` when the player stands up, which is what that code did
  until 2026-08-20; §6 kills a player, stands them back up through BOTH revive
  configurations (the shipped one-tick defer and `RURIK_REVIVE_DEFER=0`) and
  reads the maximum that goes out. §5 asserts the death tick is ArenaNet's own
  order — status bit, `0x009C` absolute morale, `0x00EE` delta, energy max,
  energy regen, health max — with the delta carrying the wire's own
  `0xFFFFFFF1` rather than a sign convention of ours, and every message of it
  encoding through the codec. **§9 is the resurrection grace window** (GWW:
  "Dying shortly after resurrection (5 seconds in PvP, 14 in PvE)" never incurs
  a penalty): the boundary is pinned at both ends, the FIRST death of a session
  is required not to be free — `revived_at == 0` answered by a guard rather
  than by arithmetic, or a server eats everyone's first death — a waived death
  is required to put NO morale message on the wire while still leaving the
  player dead, and the CONTROL is that the revive path stamps the window
  itself, without which the whole rule could only ever fire in a test that set
  the timestamp by hand. §8 pins the other half of the original
  question: `0x00E9` field 10 stopped being one of the zeros this server
  sends, because retail carries 100 there in 43 of 43 sightings and 0 is
  not a legal morale at all. Floor 60, against a green 61/60 across the two
  revive configurations. No vault, no socket, no client),
  `toolkit/clientscan/test_moralestore.py` (the morale-store scanner, proven
  against a process this machine controls rather than against the game. It
  exists because the tool's headline output is a NEGATIVE as often as a
  positive — "nothing in this window ever changed" is what "the delta is
  ignored" would look like AND what a scanner that cannot see anything looks
  like, so the null needs a control before it is evidence. A child process
  holds a constant at a known address and walks a value through 77 → 88 → 66 →
  53 beside it; §1 requires the region walk to actually read megabytes and to
  find the child's own address, §2 requires the watched window to record all
  four values in order and its NEIGHBOURS to record none, §3 measures the
  coincidence rate that broke the first MORALE-Q7 attempt (22,304 hits for the
  value `1` against 4 for the anchor 424242 — which is why the method locates
  on a constant the experiment never changes), and §4 requires an unmapped
  address to read as None rather than as zeroes. Floor 8, Windows-only,
  skips honestly elsewhere. ~10 s),
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
  a measured CAUSE: the hatcher's bound diffuse texture carries alpha ~0 on
  99.9% of its texels and the inherited prop convention wired texture alpha
  as transparency, so the default render was a floating head over an
  invisible torso, and --opaque tripled the coverage (0.0147 -> 0.1932).
  **THE ALPHA ARM HAS SINCE MOVED, and the checks moved with it.** The
  terrain arc fixed that cause upstream (FINDINGS 7.17: `_alpha_class`
  calls this texture an "eraser", `gwmodel_materials` skips the wiring for
  that class alone), so both arms measured 0.1932 and the >=3x gap check
  became one that could not fail either way -- the suite's only
  pre-existing red, 2026-08-18. It was REWRITTEN to assert the new truth
  rather than relaxed, in four parts, because the obvious single
  replacement is vacuous: "default == opaque" is satisfied just as well by
  a viewer that has stopped wiring alpha ENTIRELY. So: the classifier's
  verdict is named in section 2 (a decoder fact, checked without Blender --
  the eraser list is exactly [tex_1C7DB.png], since a count would pass if
  the verdict moved slots); (a) default and --opaque agree within 0.005 and
  both show the whole body; (b) the POSITIVE CONTROL -- a manifest copy
  with the eraser verdict reinstated (a display field no sidecar digest
  covers; load_gwmodel still verifies every sha256) collapses to under a
  third of the coverage on IDENTICAL geometry, reproducing 0.0147 on
  demand; (c) --opaque still triples it back on that tampered manifest,
  which is the original assertion kept alive on the one input where it can
  still fail. All four are MUTATION-TESTED red (wire alpha always -> a,b;
  never wire alpha -> b,c with (a) PASSING, which is the whole argument for
  (b); a no-op _force_opaque -> c; a classifier that never says "erases" ->
  the naming check and a). What the alpha channel MEANS on a unit texture
  stays NOT DECODED with the AMAT chain -- `_alpha_class` is a floor rule,
  not a decoding. Floor 76 from the green run, 23.6 s (72 -> 76 with the
  rewrite, two of its five Blender runs being the tamper arms; 71 -> 72
  with the review's real-data tiling check); sections 0-1 (synthetics + the
  resolve_outdir refusal with its positive controls and the mapexport
  delegation check) score 28 vault-less and go RED; with the archive but no
  Blender, 54, also RED),
  `toolkit/mapdata/test_unitauthor.py` (rung A4, the ADDITIVE path: add a 16th
  linked file to a creature's shell and one sequence record that selects it.
  Two of the three things it must get right cannot fail a checksum, cannot fail
  any of `datcheck`'s ten open-time rules, and would show up in the game only as
  "some animations stopped playing". **§2, the sequence array must stay SORTED**
  by `u32@+0x01`, because the client searches it with `std::lower_bound`
  (`0x00792DC0`) and a `lower_bound` on an unsorted array silently returns the
  wrong run -- so a key is inserted at the FRONT, the MIDDLE and the END of the
  table, since a tail-append implementation passes the last of those and one key
  would not be a test. §2b then unsorts the table by hand and requires the
  refusal to fire, with a control first asserting that the sabotage really does
  unsort it. **§1, the FA8 list is POSITIONAL** -- `links[sel-1]` is how every
  existing record resolves, so the check is that the prior list is a PREFIX of
  the new one, which a reordering breaks and a length check would not. §3
  re-decodes the bytes that would actually ship and asserts the modified FA1
  re-encodes byte-identically -- the writer holding on a table it did not itself
  produce. §4 exercises the archive operation on a synthetic fixture and
  requires the ten rules plus the CRC sweep. Floor 30, and the number that
  justifies the whole rung is in §3: the edit costs **+29 bytes on a 29,802 B
  shell**, not a rewrite of the 1,514,855 B link the arc was blocked on.
  Sections 1-3 read `vault/dat_study` READ-ONLY and declare a printed skip
  without it; §4 builds its own archive and always runs. No client, no server),
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
  `vault/exports/unitwrite/`),
  `toolkit/test_bareimport.py` (the SERVER must import on a machine with no
  vault -- proven in a subprocess, not argued. **What earns it: on 2026-08-15
  `probes.py` grew `GIVER_NPC = npc_template("def_1480")` at module level**, and
  `def_1480` is a bulk-extracted live NPC definition that exists only in
  `vault/content/npcs.toml`. From that commit `import authsrv` raised
  `ContentError` on any bare machine -- the server's own import, not a test's --
  and nothing went red for three days, because the suite runs where a vault IS.
  Twelve tests died at import, four of whose docstrings say "no vault, no
  socket, no client" flatly (`test_ping.py`, `test_dispatch.py`,
  `test_population.py`, `test_killwindow.py`). **They did not fail their floors**:
  the exception escaped before `checks.py` could rule, so a bare run produced a
  traceback rather than a verdict naming the shortfall -- which is the same
  defect as a missing floor, approached from outside the ledger. §0 imports
  `authsrv` with `RURIK_VAULT` aimed at a path that does not exist; its CONTROL
  is load-bearing, because "the server imported fine" is also what a stand-in
  vault silently resolving to the real one would print, so the control demands
  that `def_1480` still be UNREACHABLE in that same subprocess. §1 imports
  `probes` alone, since an import chain that routes around the bind today could
  stop tomorrow. §2 is the half that survives the next mistake: an AST walk of
  the server path for module-level content binds, each key resolved against
  `content.load(vault_dir="")` -- repo tables only -- and it names file:line
  rather than making someone reproduce a bare machine. It also asserts the scan
  MATCHED something (5 binds today), because a scanner that quietly stopped
  matching would pass §2 while checking nothing, which is `test_codec.py`'s
  fixture-glob defect one level up. **The fix was NOT a repo-side copy of the
  row, and §2's failure text says so**: CLAUDE.md's measurement-vs-expression
  boundary permits it -- `def_1480` names its extractor, its build and its
  provenance per row -- but those rows are only ever read to build Step
  sequences that drive a REAL CLIENT, and client builds live in the vault too,
  so on the one machine where a committed copy would be read there is no client
  to run the probe against. It would buy an import, not a capability, while the
  vault row overrode it by key everywhere the probe can actually run. The bind
  moved to call time instead (`probes.py` `_vault_npc`). Sabotage run and it
  reddens 3 of 6 with the file and line named.
  **§3, added 2026-08-31, is the same defect one layer down: IMPORTING IS NOT
  RUNNING.** §2 rules on module scope only, and its scanner docstring used to
  justify that with a claim rather than a scope — "the same call inside a
  function body is fine, because a machine that cannot resolve the row was
  never going to reach that function". A bare machine reaches
  `handle_skill_press` on the first skill any client presses, and
  `player_rank_for_skill` read the vault-only `skills` table there with no
  fallback, so the server logged `skill_timing`'s "lifecycle timings fall back
  to 0" for skill 42 and then died on that same row two lines later, taking the
  connection thread with it. No scan here could see it. So §3 EXECUTES a press
  in a vault-less subprocess and requires the E4 to reach the wire, with a
  CONTROL asserting `ENERGY` is on in that subprocess — because with the gate
  off the press never performs the read, and a green §3 would then be exactly
  what the defect produced. Reverting the server fix reddens §3 with the
  `ContentError` quoted in the failure line, ON A MACHINE THAT HAS A VAULT,
  which is the property that matters: the suite runs where the vault is.
  Floor 6 → **8** = the healthy count: nothing here can skip, which is the
  whole claim. <1 s),
  `toolkit/mapdata/test_datledger.py` (the ROW CENSUS, the counting convention
  it refuses to choose between, and WHICH VERB FAILED. Correction C-8 records
  two censuses of "the same" archive disagreeing by 16 comp-8 rows and 20 in the
  sum, load-bearing on the published "661 of 138,708 rows are unwritable stored"
  -- and the headline here is NOT the counting: "26 rows censused" is a number
  an almost-right census also prints. The load-bearing fixture is a PLANTED
  DISAGREEMENT, one compression-8 row with FLAG_ENTRY_USED clear, which the
  `entries` convention counts and the `used` convention drops; section 3 asserts
  BOTH counts, that they differ by exactly the rows the delta names, and that
  the delta decomposes into `{structural 12, spare 2, comp8 1}` -- the mechanism
  in miniature. The synthetic archive carries every class at once (fifteen
  structural rows, two spares with one still named by the file-id table, an
  armed head, stored rows, real `gwenc` compression-8 streams, an unknown
  compression code 12, a bit-31 renamed row, the ghost row) and its MFT is
  deliberately not a block multiple, so row 3's slack is checked against
  `datalloc.mft_slack` -- two modules, one number, neither importing the
  other's. **The second thing it exists to do is refuse to bucket a row it does
  not understand**: the ladder always terminates, so every row lands somewhere
  and the totals always look tidy, which is the shape of a check that cannot
  fail. Section 5 pokes each of the six contradictions into a copy's MFT and
  requires the row to be REPORTED as well as bucketed. **The third is section
  6b, which is about WHOSE FAULT a failure is**: review found `--reencode 9999`
  printing the entire census -- headline, classes, slack -- and then reporting
  "could not census DAT" with exit 2, the code this directory spends on an
  unreadable archive, a false statement about a file the same run had just
  finished reading and the sort a script believes. A run has four verbs and only
  one is the census, so `_phase` makes each name itself and the last-resort
  handler stop claiming to know; 6b asserts the census RAN and printed, that the
  refusal names the ROW and not the archive, that a corrupted comp-8 stream is a
  failure to re-encode THAT ROW, that an unopenable `--json` destination is a
  failure to WRITE, and -- the control that keeps those three from passing
  vacuously -- that a genuinely unreadable archive still does say "could not
  census". The PRE-FIX module, restored verbatim in memory, reddens eight of
  6b's eleven; the three it does not are exit 2, the census-printed-first
  premise, and that control. Sabotages are run in memory and counted, never
  predicted: the anomaly walk stubbed out reddens 9 while printing the SAME
  class totals; classing on `size == 0` alone -- the pre-2026-08-15 `datplan`
  rule that called an ARMED head a free slot -- reddens 6; `reservation_for`
  without block rounding 7; `check_stamp` that never compares 3; `_phase`
  neutered 4; `reencoded_size` without its row-range refusal 3; the convenience
  `file_id_table(raw=False)` 1. The first sabotage FOUND a defect in the module:
  `_by_class` was a comprehension over `CLASSES`, so a class the ladder produced
  and `CLASSES` omitted vanished from every total while every total still added
  up -- the same failure the anomaly walk exists to prevent, in the code that
  reports it. Two test-side helpers exist for the same reason and are worth
  reading: with a naive `.splitlines()[1]` detail expression the stamp sabotage
  raised IndexError INSIDE the check's own argument list, killing the section
  and leaving one unnamed crash as the whole evidence (`line()`,
  `refused_line()`), and `refusal()` catches only `Refused`, so a bare
  IndexError where a refusal belongs would have escaped the check written to
  catch it (`raised()`). Section 3b walks the module's own syntax tree and
  requires C-8's figures to appear in the docstring citation and in NO other
  literal, with a control that they are in the docstring so the check cannot
  pass vacuously on a module that never heard of the correction. **Section 7 is
  where C-8 comes apart**, on real archives -- and since the 2026-08-27 resync
  Route E is read from **`vault/dat_study_38797`**, the copy it was MEASURED on,
  rather than from `vault/dat_study`, which is now 38833 (`studies/maprows`
  sec.10.14). There it still reproduces the larger census EXACTLY (38,633 = the
  "38,621+12" whose +12 IS the twelve erased structural rows the USED convention
  drops, 138,708 comp-8, sum 177,341), and the pristine install copy under `used`
  reproduces the smaller SUM exactly (177,321) with the compression split one row
  from what was reported -- so the twenty rows are SEVEN of archive difference
  plus THIRTEEN of convention, and the sixteen comp-8 rows are FIFTEEN plus one,
  and the reconciliation closes. C8_ROUTE_E and C8_ROUTE_C are transcriptions of
  a PUBLISHED correction, never measurements of ours, so re-pinning them to
  whatever the current archive says would make the test agree with itself and
  delete the only check that C-8's figures were right. Section 7a was rebuilt as
  generation-INDEPENDENT relations for the same reason, which incidentally killed
  three latent defects it had been carrying: a literal standing in for a live
  census, a telescoping identity that could only fail when another check already
  had, and a one-way guard whose message claimed "either copy". Floors are three
  shapes with ZERO headroom each, all MEASURED: 84 bare (`RURIK_VAULT` pointed at
  nothing), 94 with a vault, 97 when the Route E archive is present -- and the
  ordering is load-bearing, the vault floor and the anomalies check sitting
  BEFORE the early return so a machine without that copy keeps the vaulted guard
  rather than silently dropping to the bare floor. ~2 s),
  `toolkit/mapdata/test_refindex.py` (the REVERSE-CLOSURE index -- "who else
  reads this row?", the question `unitassembly.py`'s forward walk cannot answer
  and the shared-skeleton hazard (`studies/unitmodels/FINDINGS.md` §3.11, six of
  seven pairs bit-identical) needs answered before a write. Builds its own
  archives: the MFT, the ffna type-2 container framing, the reference-list
  record rule and the FA1 blk2C layout are all re-derived from this file's own
  byte literals and nothing is constructed by the module under test. **The
  positive control is section 1 and it is not a formality** -- an FA8 link is
  planted from two heads onto a third and BOTH must come back kinded before any
  section reads anything into an absence, because a tool whose every answer is a
  FLOOR fails by answering EMPTY and an empty answer looks exactly like success.
  Covers the KIND (A reaches T through FA5, B through FA6), the dedupe (an FA8
  naming a target twice is ONE referrer), the FA5 null slot naming no file and
  therefore no reader, an unresolvable target recorded in `index.unresolved`
  rather than dropped, `m_seqCount` recorded as a fact and NOT applied as the
  client's link gate (`0x00794917`), the flags-1 companion row that links to the
  same target and is correctly not walked, and walked-vs-indexed reported
  separately so two unreadable heads cannot quietly shrink the archive.
  **Section 3 is the defect this module shipped and it is the reason the graph
  is keyed by MFT ROW**: a row can carry several file ids -- 38,396 do on
  `dat_study`, 60.0% of all flags-515 heads and 25,536 rows that are not heads
  at all -- and edges filed under whichever spelling a reference list happened
  to use made ONE physical row answer two different things, 558 of 558 times on
  a 1,500-head sample, one of them the confident empty list. So it asks every
  spelling of a two-name TEXTURE row (flags-3, not a head, the case a head-only
  alias map cannot resolve), of a two-name head row, and of a bit-31 rename
  spelling; checks `canonical_id` normalises a caller's own ids the same way;
  and cross-checks `who_reads` against `unreferenced_fa1_heads` for the
  contradiction that defect produced -- no two spellings of any head disagree,
  and no head the census calls unreached answers with a referrer under any of
  its names. Skeleton sharing is bit-identity and section 4 does not weaken it
  -- two heads with identical blk2C bases pair, a third with the SAME node count
  and different bases does not, a fourth with an extra node does not -- **but
  the answer now carries the node count, the group size and whether every base
  in the key is zero**, in the sentence and in `answer.facts`, because on retail
  572 of the 1,003 FA1-carrying heads in a 1,500-head sample sit in ONE group
  keyed on a single node at (-0.0,-0.0,-0.0), and a bare count would send an
  operator off to acknowledge 571 unrelated models; a +0.0 twin is contentless
  AND in a different group, which pins that "contentless" is a REPORT and not a
  change to the criterion. **The sabotage** cuts the terminator off the planted
  FA8 record: the build must land it in `index.problems` at `mdlrefs`' own
  `G01_terminator` gate, DROP that referrer rather than invent one, still report
  the intact referrer, and still index the same head's FA5 list -- a refusal
  scoped to the head instead of the list would look identical on a green run.
  Also the stamp (size + MFT sha256) refusing a stale index against an archive
  edited to the SAME size and row count, six doctored-index refusals including a
  format-version bump and a document with no spelling map, `save` refusing a
  path inside a checkout and writing nothing, the floor sentence and the
  skeleton facts surviving a JSON round trip, and the CLI exiting 2 on an
  unreadable archive and on `--json X --build-json X`. Eleven in-memory
  sabotages were run and all eleven reddened NAMED checks
  (19/12/11/8/7/5/5/4/3/2/1); three were hard stops until `first_spot()`,
  `head()` and `fact()` were made to read defensively, which is why they do. 92
  checks against a floor of 92, no vault, nothing that can skip. ~0.25 s),
  `toolkit/mapdata/test_datdelta.py` (CONTENT-ADDRESSED ROW DELTAS -- a staged
  archive IS its difference from retail, so the 4.2 GB copy can be deleted, and
  this is the file that says whether it may be. Ten sections against files it
  writes in a temp directory, with `RURIK_VAULT` pointed at another one so the
  store guard runs for real rather than being skipped; no vault, no corpus,
  nothing that can legitimately skip. The span finder is checked against
  arithmetic done by hand -- 63 B of agreement between two differences merges,
  64 B splits, a difference across a chunk seam is ONE span -- then
  capture/apply/prove round-trips byte-identically in BOTH directions, including
  a staged archive that GREW, where the tail past retail's EOF is one span whose
  retail side is zero bytes long and reconstituting back TRUNCATES. Section 4 is
  the long one: an unrelated target, a target that is already the destination, a
  blob of the wrong LENGTH (five bytes where the span declares six -- it used to
  be six WRONG bytes, which fired the hash branch and left the length branch
  with no coverage at all, and disabling that branch alone kept the whole file
  green), a blob of the right length and the wrong bytes, a missing blob, four
  doctored manifests -- one the structural check can see and three only the
  destination sha256 can, because a span shifted within range, a span whose two
  sides are swapped and an emptied span table are all structurally flawless --
  and TWO SPANS NAMING ONE BLOB, the dedupe the tool advertises, which is where
  a table declaring two different lengths for that blob used to walk past the
  store verification and spin `apply` for ever on a spent file handle. Every one
  of those checks the TARGET as well as the message, because a refusal that
  arrives after the write has refused nothing, and the two calls whose broken
  form is a hang run on a join deadline so the defect lands as a named FAIL
  instead of a cursor. Section 6 is the store: blobs paid for once across two
  deltas, a two-manifest store with no `--name` refused rather than guessed, and
  the same rule on the WRITE side -- capturing over a manifest that describes a
  different pair refuses naming both hashes, an identical re-capture is
  idempotent and says so, an explicit `--name` is no licence either, and
  `--replace` is the only way an overwrite happens (`run/Gw.dat` and
  `run-live/Gw.dat` both stem to `gw`). The span cap is exercised for real at
  4,100 genuine spans (266,500 B of fixture); the 256 MiB byte cap is exercised
  by tightening the constant, which is stated rather than hidden. Section 8
  builds a real 14 KB archive so the row annotation runs against a table that
  exists -- a payload span names exactly its row, a span inside the MFT names
  row 3 and is flagged -- and a file that is not an archive still captures, with
  the reason in a note. Three sabotages live in the file for guards nothing else
  can reach: `apply` stubbed out entirely so `prove` must say NOT PROVEN on its
  own hash, `_verify_blobs` stubbed down to a sha-to-path map so the write loop
  must refuse a spent blob by itself, and the byte cap tightened. Fourteen more
  applied by source surgery and reverted, worst 9 red for `_verify_blobs` sizing
  and hashing nothing; the counts MOVED between sweeps until they were re-taken
  with `-B`, because several sabotages add exactly ten characters and CPython
  will reuse the previous same-size source's `.pyc`. Floor 84),
  `toolkit/mapdata/test_overlay.py` (DECLARATIVE ARCHIVE PROFILES, and the
  refindex gate is the thing being proved — from BOTH sides, because the gate
  has two ways to answer emptily and each has its own positive control. Section
  3 is the first: two heads are planted linking to the edited row and the plan
  must REFUSE naming both — printing refindex's own floor sentence and blind
  spots verbatim, plus the exact `acknowledge_shared_with = [...]` line to paste
  — before any passing case below it is believed, because a bounded query fails
  by answering EMPTY and an empty answer is the shape that looks like success.
  The tier is checked from both sides: a real two-node bit-identical rig must be
  acknowledged, while an all-zero degenerate key (572 retail heads sit in one
  such group) must print its note, say outright that nothing is required, and
  refuse nothing. Every id crosses `refindex.canonical_id` on both sides, so the
  fixture gives row A two plain spellings — 60% of retail heads are multiply
  named — and a COMPLETE declaration written in the other spelling must PASS
  while a PARTIAL one in that spelling must still refuse naming only what is
  missing. Section 3b is the SECOND positive control and it is about the INDEX
  rather than the archive: a stamped, current, non-partial index still answers
  EMPTY for a row whose only referrers are heads it could not READ, so A and B
  keep their real FA8 lists naming C and have their container magic damaged to
  `ffnX` — the archive proven healthy on all ten rules and every crc, the index
  proven current with problems 2 and partial False, `who_reads(C)` proven `[]`,
  and only then is the refusal believed. The blind spot must be declared by
  COUNT (`accept_unread = N` in `[overlay]`), refused when undeclared, refused
  when the number has moved in either direction, and NOT waivable for a partial
  index, which gets no acknowledgement at all whether handed in or saved and
  named by a manifest. Its sharpest check is the contrast: the same texture edit
  against the archive whose containers DO read is refused for a real FA5
  referrer, so the empty answer was the damage and not the truth. Also there: an
  id the index resolves to no row says so out loud instead of passing silently,
  a row that is ITSELF unreadable says that its empty co-wearer answer means
  "not indexed" and never "nobody else wears it", and a file-id table poked in
  place — which leaves the MFT stamp byte-identical, asserted, and which only
  `--crc-sweep` can see, also asserted — makes the index and the archive name
  two different rows for one id and is REFUSED naming both. Section 7 is a
  sequence with no client in it: `--build`, `--deploy --yes`, `--retail --yes`,
  `--verify-after` used to end with the post-flight naming a row `--retail` had
  rewritten seconds earlier as one "the client wrote to", so the section runs
  that exact sequence and requires a refusal, runs the re-build variant and
  requires another, requires the two halves of a before-image to describe one
  deploy (the record carries the snapshot's sha256), requires a hand-edited
  before-image to be caught by its own digest, and requires the result to NAME
  the moment it was measured against. Also: manifest refusals (unknown [overlay]
  key, a name that is not [a-z0-9-]+, active==retail, two edits on one file id,
  `stored` beside compression 0, C:\gw as EITHER archive); the fit arithmetic in
  all three cells by hand, including `fit_of(100, 900, 600)`, the only pair of
  numbers that can tell a donor-sourced grow_to from a payload-sourced one; a
  file id named by two records refused rather than resolved to whichever sorts
  first, with the silent `file_id_table` answer measured first as the sabotage
  premise; `datwrite.declaration_fault` wired, so a compression-8 stream that
  decodes to bytes other than its declared payload never reaches the archive; a
  saved index loaded stamp-checked and a stale one refused both when named and
  when handed in; build staging under the vault, byte-exact on the touched row
  and untouched everywhere else, refusing a build that changed nothing; a
  hand-edited build record caught by its own digest; the grow-back run for real
  against a row shrunk to 100 B with its own 1,024 B standing free, datwrite
  annexing and the journal recording the whole reservation; the three-valued
  deploy premise with --yes on both writing verbs and a NEITHER state
  hard-refused; verify-after detecting a simulated client write on an owned row
  while reporting the archive itself still healthy; and the CLI's one-verb rule
  and 0/2 exit codes. Builds its own archives, manifests and payloads in a
  tempdir with RURIK_VAULT pointed at a temp vault, so there is no corpus to be
  missing and nothing here reads the real one. Twenty-two sabotages measured,
  and every one of them runs all 133 checks — an earlier pass had three that
  CRASHED the run at checks 46, 51 and 74 and scored 0, 0 and 7, which is why
  `Ran`, `state_of`, `health` and a defensive `row_bytes` exist. Floor 133),
  `toolkit/harness/test_abrun.py` (A/B DIFFERENTIAL RUNS, THE MECHANICAL HALF —
  no client, no vault, every fixture built in a tempdir: the gamesrv logs, the
  capture directories, the manifests, the archives. Section 0 is the log-line
  contract twice over: each counter must match the server's own format AND each
  producing print's distinctive fragment must still be present in `authsrv.py`,
  which is what goes red the day somebody rewords one. Its near misses carry the
  real double-count hazard — `authsrv.py:7064` echoes every send as `[c3] s2c
  agent 41 casts skill 1234 (0x0057, 12B)` using the label written one line
  above the cast print, so a looser pattern counts every cast twice at an
  entirely plausible number; `WRAPPED` asks the `^`/`$` anchors separately and
  exists because the anchor sabotage first scored zero. Section 1 holds the
  ARM-BOUNDARY CENSUS with the defect as its control: by mtime alone the
  previous arm's log IS the newest one after this arm's deploy, because a stack
  goes on relaying while it tears down and `capture_error_dialog` waits up to
  twelve seconds after the client exits, so one teardown line landing during a
  4.2 GB flip is all it takes; against a census of directory NAMES taken at the
  deploy, that directory is not bindable at all. Section 2 carries its own
  positive control — a document written in place and truncated must be REFUSED
  before any claim that an atomic one survives — then kills `os.replace` between
  the fsync and the rename and requires the previous verdict to still parse.
  Section 3 opens a real Win32 handle with share mode 0 (pure ctypes: a
  byte-range lock still lets `open()` through and would prove nothing about the
  mechanism an arm's boundary is read from), skip-declared off Windows. Section
  4 drives a whole arm with a scripted client that writes log lines between
  polls; section 4b runs one arm three times against one fixture and requires it
  to read 30 hits when told nothing preceded it, ZERO with the census it takes
  for itself, and exactly its own 1 when its own capture appears mid-hold —
  thirty and thirty-one both look like a session, which is why the control is
  there and not only the fix. Section 5 is the one that matters after a crash: a
  header-CRC-poked archive must have the launch gate's refusal RECORDED and the
  arm still reach `finished`. Section 6 asks of every refusal WHEN and not only
  WHETHER — which client opens the archive is a directory listing and whether
  the build record is one is a single `json.load`, and both used to be announced
  only after a whole-file copy had landed on the shared ACTIVE archive, so both
  are asked through `--run` against a fixture whose ACTIVE and RETAIL carry
  different bytes and the check is the archive's own checksum afterwards; its
  timeouts are zero because a defeated refusal does not fail there, it reaches
  the 900 s wait and hangs the file. Section 7 holds the compare table, its
  `capture bound` row, and the three exit-1 cases a difference must not be
  confused with: an unfinished arm, two arms naming one verdict file, two
  finalised arms that bound one capture. Section 8 is REAL — `test_overlay.py`'s
  own World and rows_spec, two profiles built over one row, `abrun.run` driven
  end to end through real deploys — and it exists because the ordering defect it
  covers was invisible to every fake: two overlay arms owning one row resolved
  cleanly, played the first to a finished verdict, then hard-refused the second
  for "neither retail nor 'beta'". Seventeen sabotages measured,
  26/6/4/4/3/3/2/2/2/1×8 red, every one at full coverage. Floor 120),
  `toolkit/clientscan/test_routerbench.py` (ROUTER-B1, the committed
  RETHINK-QB analysis layer — the retail click→chain census whose numbers
  REALFIX §0.19 quotes lived in scratchpad scripts sys.path'd at a deleted
  worktree, mistakes-review class 8 made literal one session later. Guards
  `toolkit/clientscan/routerbench.py`. Section 1 is bare-machine synthetic:
  the op61-heading-vote attribution, chain assembly with its three endings
  (terminal / superseded-with-the-opcode-named / open), the leg-cadence math
  fed the 63805 chain's own transcribed grants and required to return the
  desk-skeptic's committed speeds (288.5, 282.8, six of eight within ±4% of
  288), monotone along-fraction to exactly 1.0, the dead-reckoned origin
  model (mid-leg at run speed, arrival clamp, chained legs, report reset,
  refusal with no position source), the polyline distance, op409 map-id
  read, and the heading-clip mesh check on a stub mesh with a wall
  (exact-D1 counted, agreeing truncation ≤3u, phantom truncation
  disagreeing). Sections 2–4 need the vault + `dat_study` and skip loudly
  without them. Section 2 is the FIDELITY GATE: census() must reproduce the
  committed QB numbers from the same tapes — ≥29 clicks all answered within
  one RTT, ≥16 verbatim / ≥13 part-way, zero surviving "unanswered", ≥8
  superseded, and the 63805 anchor bit-exact (nine grants, first answer
  ≤0.065 s, along-fraction monotone, terminal == click to the float).
  Section 3 locks the heading-clip mesh-identity numbers on the two
  immutable anchor connections (63805: 506/297/209/65; 62994: 98/89/9/8) —
  the corpus-wide map-280 aggregate independently reproduces Q7's 248/701.
  Section 4 scores `pathmap.route()` against retail's own answers and gates
  only the hard invariants: every routed specimen's legs clip-clean **at
  step 2.0, 8x finer than route()'s own 16u gate** (the review caught the
  default-step version re-running the gate's exact check — a check that
  cannot fail; at 2.0 it can), every terminal exactly the click (a
  pathmap-contract regression lock — route() appends the goal on both
  return paths), and ALL 13 scoreable retail-verbatim clicks
  reproduced as our one-leg case bit-identically (corpus-level counts are
  ≥-floors because the live corpus grows; bit-exact locks stay on the
  anchor files). Floor 48 from the green run. ~15 s warm),
  `toolkit/authsrv/test_router.py` (ROUTER-B2, the router click policy — **the
  DEFAULT since 2026-09-03, MOVECODE-1z-v; `--no-router` reverts** —
  the wiring's own checks, bare-machine (no vault, no client, no sockets;
  routerbench validates the pathfinder against retail, THIS file validates
  the plumbing). Section 1 drives `router_answer_click` on a stub mesh with
  one wall through all five verdicts: verbatim (speed-then-move, exact
  point, no chain, held click superseded, integrator armed), routed (speed
  ONCE then the first leg, chain armed with the remaining legs, matched
  plane pair), kbd-drop (nothing sent, read off Rule 1's latch directly so it
  survives --no-grant-suppress — ~~retail's own contract~~ **CORRECTED
  2026-09-05 (MOVECODE-1z-bh, review §1.7): the drop is OURS**, kept on
  MOVECODE-R1-B1's displacement outcome; retail answered 7 of 7 single
  mid-keyboard clicks, and `--answer-kbd-click` is the revert arm this section
  now also drives), refused
  (origin-off-mesh — the P-17 wall-press door CLOSED: nothing sent, dest
  dropped, reason named in the row) and clip-fallback (the stop lands short
  of the wall, never past it; the route-refusal reason rides the row), plus
  the no-mesh fallthrough and new-click chain abandonment. Section 2 is the
  scheduler: due = grant + dist/288, nothing mid-leg, a bare grant at
  completion (no speed row — retail's chain grammar), interior planes via
  plane_at matched, the terminal grant carrying the client-named dest plane
  and clearing the chain, and the late-poll cell that CAUGHT this file's
  own first wrong expectation: a late poll grants ONE leg (the client was
  parked — it cannot walk a leg nobody granted; cadence restarts at the
  grant instant), never the drained queue. Section 3: abandon pops, logs
  the cause and remaining count, and is silent with no chain. Section 4
  locks the wiring in source: the handler branches to the router exactly
  once and BEFORE the freshness gate, both recv-loop attach points
  game-gated, the dynamic timeout clamped to [0.05, 1.0], both report
  handlers abandoning, the keyboard drop latch-read, the no-route path
  never sending the raw dest, DEFAULT_RUN_SPEED the only speed constant,
  and all nine composition refusals present (the review round added
  --interact-walk and --move-speed-effects). The review round also added
  the sampling-gate pair — a stub route whose leg crosses the wall (as
  route()'s 16u gate could pass over a sub-sample sliver) must be demoted
  to the clip-fallback by the 2.0u pre-send re-clip — and two fine-step
  source locks. ROUTER-B4 (run 2) added seven more: route() receives the
  click's planes, corridor-true planes ride the grants (interior legs the
  corridor's, terminal the client's named plane), the tour cap refuses an
  island-tour route (the run's 11.8x specimen shape) into the
  clip-fallback with reason=tour-capped, and a short corner detour under
  the SLACK term survives the cap — the control that keeps the cap from
  eating ordinary cornering. ROUTER-B5 (run 3) added four: an
  8u-penetrated origin (the run's own measured stand) snaps and gets a
  VERBATIM answer instead of the refusal that armed the 218-second
  lock-in, the answered click resets the refusal streak, a true hole
  deeper than the radius still refuses with the reason named, and
  consecutive refusals count a streak onto every row — the run-3
  silence can never again be quiet. **2026-08-30 added five, and they exist
  because a proposed fix was wrong**: two separate analyses read the three
  UNCONDITIONAL `a2_matched_field4` call sites as a leak — a helper whose
  docstring said "for one `--d1-lead` send" being called with `D1_LEAD =
  False` — and proposed gating them. Gating them was actually *tried*, and it
  turns this file's "first leg carries the corridor's plane, matched" red:
  where field 3 is a plane WE computed, field 4 must match it unconditionally
  or the P-17 phasing door reopens on every routed leg. Only the one-leg
  VERBATIM echo gates the override, so it stays wire-identical to the shipped
  clear-line fire. The five locks pin that asymmetry (3 ungated + 1 gated),
  and pin the helper's SUMMARY LINE rather than its source — the body now
  quotes the old wording inside its own correction block, and a substring
  check fires on the quote. The real defect was the contract line, and it was
  wrong the day it was written (`8cbcbc9` created the helper; `995a515`
  added four router sites the same day and never revised it). **Section 5
  (2026-09-03, MOVECODE-1z-v) added thirty: the router is the DEFAULT with
  both conditions on, `--no-router` / `--router-raw-leg` /
  `--router-report-plane` exist and the pairwise refusals carry the
  default-flip hint; condition (a) — the click-leg record, armed on the raw
  chord by the 0x003E arm before the router runs, is re-aimed at the routed
  first leg (stamp kept as identity, its own `start`, ETA = the leg's travel
  time), each chain leg re-arms it FROM the reached waypoint and lerps from
  its own start, the clip-fallback re-arms to its stop, a verbatim answer
  leaves it alone, an unarmed record stays unarmed, and the known-bad arm
  keeps the chord; a press mid-chain abandons the chain (cause `press`) and
  PRESS ENDS THE WALK re-pins the body ON THE ROUTED LEG, not at the chord's
  (144, 0); a follow abandons it too (cause `approach`); condition (b) — the
  one-leg verbatim answer's field 4 is the mesh's plane under the modelled
  sync copy when the report's plane is not offered there, the report's
  plane where it is (wire unchanged), where the mesh cannot say, and on an
  unseeded model; the copy is modelled MID-LEG; the known-bad arm sends the
  frozen report plane; plus four source locks (the three re-arm sites, the
  two abandons, the helper before the gated match, the leg model's own
  start).** **Section 6 (MOVECODE-1z-w, same day) added eleven: the routing
  ORIGIN's plane word — the mesh under the body model, the report's plane
  where the mesh offers it or cannot say — reaches route() as its start
  preference (a body on plane-5 ground with a frozen report of 3 routes from
  5), rides every `router_route` row as `plane_origin` beside
  `plane_report`, and decides the clip-fallback's stop plane on STACKED
  ground (the one wire effect: reached from plane-5 ground, a {3, 5} stop
  carries 5 matched, and the known-bad arm `--router-report-plane` carries
  3 and tells route() 3); ordinary ground and an unknowable mesh leave the
  word at the report's; and a cast that begins abandons a live chain
  (`cause=cast`, driven through `handle_skill_press` with the recorder the
  press arm now hands it), pinned once at the begin instant before the
  cast-stop block, with the origin word derived once, after the snap and
  before route().** **Section 6 (2026-09-04, MOVECODE-1z-bb) is the SEAM-AWARE
  RAYS**: RUN-1zBA's specimen was the clip fallback walking plane-blind off a
  bridge deck's side and granting the 2 km beyond it, so both of the router's
  rays — the pre-send leg gate and the fallback — now come through
  `_router_clip`, which calls the mesh's `seam_clip` on the body's plane under
  `ROUTER_SEAM_CLIP` (default on) and plain `clip()` under
  `--router-blind-clip`. The stub mesh grows a fake blind seam (`seam_stop`, a
  vertical line short of its wall): the fallback stops AT the seam, and under
  the known-bad arm walks through it to the wall (RUN-1zBA's grant); a stub
  route whose leg crosses the seam is demoted to the fallback, which itself
  stops at the seam, and the known-bad arm grants that leg verbatim; source
  locks pin the flag's default, that `router_answer_click` reaches the mesh's
  ray only through `_router_clip` (three occurrences file-wide, two in the
  function, no bare `pm.clip(` in it), and that the one flag sets
  `pathmap.SEAM_AWARE_ROUTE` too, so route()'s own pull and gate cannot
  disagree with the fallback. The fine-step source lock for the fallback
  follows the call through the helper. **2026-09-05 (MOVECODE-1z-bh, review
  §1.7) added five to section 1: THE KEYBOARD DROP'S REVERT ARM.** The drop
  was documented in three places as retail's contract and it is ours —
  REALFIX §0.15 is a rapid-PAIR rule, §0.14's V-RETAIL-2 measured retail
  answering 7 of 7 SINGLE mid-keyboard clicks — and `--answer-kbd-click` was
  read only by `_grant_verdict`, the legacy path `router_answer_click`
  bypasses, so under the shipped `ROUTER = True` the flag was inert and the
  drop had no arm that could convict it. The flag now reaches the router, and
  the same click is driven both ways: OFF is the kbd-drop row (existing), ON
  is a grant on the wire with the real `verbatim` verdict row and a
  `kbd-answered` PASS-THROUGH row marked `arm`/`pass_through` so a click
  census can filter it, with the module global restored and re-asserted after.
  Floor 126 from the green run (51 at the B2 landing, 57 after the review
  round, 64 after B4, 68 after B5, 73 after 2026-08-30, 103 after 1z-v, 114
  after 1z-w, 121 after 1z-bb). ~1 s).

`toolkit/authsrv/test_agtrack_mirror.py` (**the AgTrack mirror's transcription,
  rule by rule -- MOVECODE-1z-q step 1's guard.** `agtrack_mirror.py` is a
  server-side transcription of the client's history chain and reprieve test,
  and every one of this file's checks pins one decoded behaviour to its
  citation: the bake equations and the zero-distance short-circuit, the
  dead-reckoner and its deliberately-absent destination clamp, the arrival
  teleport's writes (including +0x48 cleared to keep AgAgent.cpp 2090's
  invariant), the recorder's 7-field push rule with both timers and the
  destination-vs-position seed arms, the walk's oldest-match-wins truncation
  with the seed as segment 0's far end, seg_match's degenerate/lerp/verbatim
  arms and their plane words, gate 1's exact 89600.0f squared threshold (a
  true 300.0 u separation SNAPS), gate 2's off-mesh-start snap, the
  clientControlled fences (a fence-closed grant APPENDS -- round 5's
  "client only is REFUTED"), 0x002C's Clear-then-set-then-append order,
  re-arm's edge trigger that nulls the head but never the seed, the MISS
  consequence chain, 0x002B's store-only semantics, and reader 2's
  parameterized prune. Synthetic throughout: no vault, no client, bare
  machine. The corpus replay itself is `toolkit/clientscan/agtrack_replay.py`
  -- a tool, not a suite test, because its ground truth is the growing
  gamesrv corpus and a pinned count there goes stale the next time the owner
  plays (the corpus-counts-redden rule). Floor 64 from the 2026-08-30 green
  run. <1 s **§17 (NPCTRACK-F14, 2026-09-06): the client's AGENT-AVOIDANCE pass on the sync copy.** The shared setter runs `0x006011F0` over every other agent right after the bake and the tick re-runs it at the collision deadline it arms (movecode §1z-be.2; the tail decoded in npctrack F14). `SyncAgent.avoid` transcribes it -- closing, the 60° cone (`0x009458BC`), overlap at combinedRadius 80, then the sidestep computer's exits in the client's order (disc covers `m_targetPoint` / off-mesh -> HALT at `0x00601899`; else the waypoint bake with bit 18, `start + perpendicular-away × ((R + 10) − |distFromLine|)`) and the tick's waypoint re-bake toward the wire point (`0x006002B5`). The section pins each tape shape: the first press (parked hostile 75 u dead ahead fires AT THE SETTER, 90 u left, target kept, arrival 312 ms, then the re-bake and -- outside the cone -- NO second sidestep on a 520 u lead), the 200 u lead where the resumed leg re-enters the disc inside the cone and sidesteps again by 38.7 u from the dead-reckoned point (F11's short second legs), the cone at 55° (fires) against 65° (walks past -- the tapes' 29 quiet grants), a separating obstacle behind, THE HALT (a 76 u lead ending 35 u from the parked hostile: v = 0, both target blocks invalid, unmoved -- the wall silence on RUN-R1/R2/R3, 14 of 14 on the tapes), the deadline arm (200 u ahead fires nothing at the setter and the ticks fire at contact, 1,424 ± 16 ms, from x ≈ 120), a head-on mover met at (300−80)/576 ms, a mesh that refuses the waypoint (halt), a grant mid-sidestep (bit 18 cleared, re-aimed from the dead-reckoned point, retry reset), and the REVERT ARM plus the no-provider vacuity control (both walk the first-press shape straight -- the known-bad arm the tapes measured at ~100 u). Scored before shipping on seven tapes / 232 player grants: 24 of 26 sidesteps to 0.2 u median, 14 of 14 halts confirmed by the tape (`studies/npctrack/FINDINGS.md` F14). Floor 68 → 92 from a real green run of 92. **§10b (MOVECODE-1z-bf, 2026-09-04): gate 2 tolerates the mesh's edge rounding.** Every gate2-offmesh re-pin in the corpus (17 fired, 19 predicted, 1,123 runs) was a false veto on a point ≤ 0.5 u outside our trapezoid edges where the client's own body stood and its own snap test passed (RUN-1zBD, two hooked runs). `MeshAdapter.start_walkable` now asks `on_mesh(a, GATE2_SEAM_TOL)`; the section runs a sliver stub under BOTH arms — tolerance 1.0 passes it, 0.0 (the `--agtrack-gate2-exact` revert) still fails it, so the known-bad arm still reproduces the false veto — plus the fallback for a mesh with no `on_mesh()` and the cross-pin `GATE2_SEAM_TOL == pathmap.SEAM_TOL`. Floor 64 → 68),

`toolkit/authsrv/test_agtrack_guard.py` (**§9 is MOVECODE-1z-bt: THE FRESHNESS GATE STANDS ON AGE ALONE.** The stationary waiver (1z-ah), its walk-start clause (1z-bn) and its newest-must-be-stop clause (1z-bs) were DELETED on 2026-09-05 (PLAN §7 Q15, the owner's ruling); their history is FINDINGS §1z-ah…§1z-bt. §9 now pins: source locks that the switches, the predicate, the report-kind bookkeeping, the three CLI revert flags and the header keys are gone and the gate is one age comparison, plus a positive control that the companion-module header sweep still records a planted bool; RUN-1zAB run A's shape (three reports on one point under a 520 u lead at the capture's 190.08 u/s) — the risk predicted with the arrival still ~0.425 s out, the re-pin BLOCKED / `stale-report` whatever the kinds, and the arrival MATURING in the mirror (the accepted cost, stated); RUN-1zBL's leg shape BLOCKED, with the gate pinned at exactly `REPIN_MAX_REPORT_AGE` (just under DUE, just over BLOCKED); a double-walk-start opening BLOCKED; the `{walk-start → stop}` opening the last shipped clause still waived BLOCKED — the deletion's one behavioural delta, red on the 1z-bs build; a walking body never proposed; a fresh report DUE whatever the pair; rate / rejects / unseeded named; the click glide still feeding `_async_est` and any report ending it; the telemetry row naming the blocker; a `0x002C` clearing the keyboard leg record. Floor 116 → 74 from the 2026-09-05 green run, then **74 → 81 at MOVECODE-1z-bv** with the new §14 below, then **81 → 89 at NPCTRACK-F14 (2026-09-06) with §15: the obstacle feed.** The server hands the guard a provider in SECONDS (`set_obstacles`); the mirrors ask in their own ms clock, so the guard's epoch sits between them, and the check pins the instant asked (the emit's own), that a parked hostile 75 u ahead of a 520 u lead sidesteps the mirror AND the twin (a sidestep is a client behaviour in both worlds), that `set_obstacles(None)` detaches both, that `MIRROR_AVOID` ships ON with `--no-mirror-avoid` in the capture header, and that `authsrv._npc_obstacles` answers a modelled hostile at its CLIENT MODEL's dead-reckoned point and velocity (900 − 144 at −288 u/s), an unmodelled agent at its server position standing, and never the player. The rest is **the derived pre-emit grant rule,
  clause by clause -- MOVECODE-1z-s.** `agtrack_guard.py` is the policy layer
  over the AgTrack mirror: the three-zone structure the decoded machinery
  forces (green = in the 100 u tube, MATCH, nothing can snap; yellow = gates
  territory; red = >= 299.332591 u or off-mesh, where ANY evaluation snaps and
  no 0x0029 can recover -- only the 0x002C re-pin, which Clears first so no
  test runs behind it). This file pins: the constants are DERIVATIONS,
  cross-pinned against authsrv's own resync constants so two derivations of
  one bound cannot drift (max report age = R_MATCH/288 exactly; min interval
  under 299.33/576); HOLE D's seeding contract (unseeded = NOT_READY, never a
  pass); the veto including the error-budget arm (modeled sep + 288*report_age
  + 10 u clock skew crossing red vetoes a gates-pass); the re-pin
  preconditions (freshness, the refused-report hole, rate -- each exercised
  both ways); clause 2's arrival-risk check, which closes p5-resync-disarm's
  HOLE A because the mirror KNOWS every arrival tick; the fence-closed
  composition (re-pin then grant APPENDS -- safe by the dispatcher fence
  0x00606002, so the replace sequence needs no luck); the two-world join (the
  main mirror applies every predicted reset, the TWIN only our own 0x002C --
  reality is bracketed and a red grant is vetoed if EITHER world says snap);
  and that prediction is pure; plus section 12, THE ACTIVE ARM --
  `authsrv._agtrack_maybe_repin` driven with a choke-faithful fake send:
  fires exactly one 0x002C on a predicted snap with a fresh report, payload
  the CLIENT's own report never ours, both mirrors Cleared through the one
  choke, no second fire, staleness/flag-off/bad-plane refusals. Synthetic,
  bare machine. The corpus retrodiction lives in `agtrack_replay.py
  --policy` (217/251 corpus warps pre-empted, 10/10 in the current regime
  -- FINDINGS 1z-s). Floor 49 from the 2026-08-30 green run. ~2 s **§13 (MOVECODE-1z-bf, 2026-09-04): the gate-2 tolerance is a recorded, revertable switch** — `AGTRACK_GATE2_SEAM` ON by default and swept by `capture_flags()`, `--agtrack-gate2-exact` present and zeroing the mirror's constant (source lock), and the mirror's gate 2 reading `on_mesh` under the tolerance and `walkable()` without it (source lock). Floor 74 → 77), **§14 is now MOVECODE-1z-bv (2026-09-05): the gate-2 branch driven THROUGH the guard.** Every other fixture in this file passes `mesh=None`, so `gate2-offmesh` had never been executed by a test — it was covered one layer down in `test_agtrack_mirror` §10b. §14 pins: the branch is reachable and is genuinely gate 2 (gate 1 PASSES at 100 u separation, so a gate-1 fixture cannot masquerade as coverage); a **vacuity guard** — the identical geometry on a walkable mesh is not a gate-2 veto, so the mesh is what drives it; and the three re-pin arms over a gate-2 want — fresh MATURES (the corpus's 17, every one fresh), stale is BLOCKED with `repin_block_reason` naming it, and **stale + coincident + newest-a-STOP is still blocked**, which is the deleted waiver's own licence shape and reads `("due", "gate2-offmesh")` on `30159d9`. That last one was WRONG on its first draft — written with two walk-starts it passed on the old build too, because 1z-bs's own clause refused that pair; the known-bad arm caught it and it was re-aimed. Floor 74 → 81. **The old §14 and §15 (the waiver's walk-start and newest-must-be-stop clauses) were deleted with the waiver at MOVECODE-1z-bt** — their history is FINDINGS §1z-bn and §1z-bs, and §9 above is what replaced them),
