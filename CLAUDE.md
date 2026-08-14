# CLAUDE.md

Rurik is a private, local Guild Wars 1 server emulator plus a content toolkit. The
strategy is in [HANDOFF.md](HANDOFF.md), the corrected mechanism and the ladder in
[PLAN.md](PLAN.md), and every operational procedure in [RUNBOOK.md](RUNBOOK.md).
Read those rather than re-deriving them here. This file is the house rules.

**Where the project is: [PLAN.md](PLAN.md) §3, and nowhere else.** That table is the
single status authority, dated and stamped with a commit hash per rung. This file and
`RUNBOOK.md` deliberately do not restate it — they did, they disagreed, and the newest
of the three was 40 hours stale. `PLAN.md` §8 is the live next-actions list.

## Non-negotiable

- **Provenance gate: zero ArenaNet bytes in the repo, ever.** No client files, no
  `Gw.dat`, no extracted assets, no decompiled code. The rationale is at the top of
  `.gitignore`; read it before editing that file. Retrofitting provenance is not possible.
  **But read the rationale's SECOND sentence too, because for four days nobody did:**
  *"Everything derived regenerates from the owner's own legally purchased install via a
  documented extraction step."* That is a permission, and it governs derived data. This
  line used to end "— only our code and our observations", which cold sessions read as
  forbidding a table of numbers read out of the client, and they refused every time: a
  derived assert table was left undecided rather than ruled on, three extracted item names
  reached a draft heading for git unnoticed, and R4c-2's unit data went unbuilt behind a
  rule that never forbade it. **Owner's ruling 2026-08-11, `PLAN.md` §7 Q3 — the gate does
  not move, its boundary is now written down, and the boundary is MEASUREMENT vs
  EXPRESSION**, not bulk vs single and not data vs code:
  - **Permitted, in bulk:** facts we measured — levels, bounds, counts, strides, ids,
    offsets, addresses, layouts — on three conditions: **the extractor is in this repo and
    the row names it, the row records the build, and provenance is per row.** Conditions 1
    and 2 are enforced by `toolkit/content.py` for `source = "client-table"` and their
    refusals are tested (`test_content.py`), because the loosening direction is the one
    where "a rule nothing checks is a wish" bites hardest.
  - **Still refused:** ArenaNet's expression — asset bytes, `Gw.dat` chunks, textures,
    audio, model data, decompiled bodies, and **bulk dumps of assert strings**.
  - **REFINED 2026-08-12, and read this before you scrub anything.** That clause used
    to end "and **verbatim assert expressions with their source path and line**", and
    on 2026-08-12 a session read it literally, found 134 citations across sixteen
    documents, and rewrote 46 of them before the owner asked whether provenance was
    starting to cost more than it protected. **It was, and all 46 were reverted.** The
    boundary now has a size term and a source term:
    **a SINGLE assert cited as the evidence for a claim is a MEASUREMENT** — keep it,
    with its file and line, because the quote is what lets a reader audit the claim
    without the binary; **a BULK DUMP is expression** and is refused; and **the crash
    dialog is not extraction** — `Assertion: X / File.cpp(N)` is text the retail client
    shows any player who crashes. `studies/smsg/FINDINGS.md` quotes 65 asserts to name
    twenty opcodes and that is correct, not debt. **The direction of error in this repo
    is over-refusal** — the three costs listed above are all refusals, and none is a
    disclosure. `toolkit/provlint.py` + `test_provlint.py` are an accumulation
    tripwire, not a gate, and there is NO obligation to hand-sweep for citations they
    miss. Full record: [studies/provenance/FINDINGS.md](studies/provenance/FINDINGS.md).
  - **Names and authored text: commit the id, resolve the string at run time** from the
    owner's own archive — `model_id = 419, name_string_id = 2519`. This is the pattern
    `mapbuild.py` already proves with FINDINGS 14's five mandatory chunks.
  - **This does not touch the second gate.** `PLAN.md` §6.1's derivation register is about
    *other people's* work and is a licence question. "We relaxed provenance" never covers
    both.
- **The vault stays local.** `vault/` holds captures, keys and client snapshots. It
  is gitignored, it is personal data from the owner's own account, and it never goes
  on the internet. Probe output goes there too.
- **Never point a client carrying OUR Diffie-Hellman parameters at the real service.**
  It does not fail cleanly — it delivers a stream of garbage frames to ArenaNet's auth
  server, *after* completing a real Stage A login with whatever credential the client
  autofilled. "Patched" is the wrong word for the rule: of the four patches
  `make_custom_client.py` applies, only the DH substitution disqualifies a client; the
  updater kill switch and the multi-instance NOP are wanted on both configurations.
  **Whose DH a build carries is what decides where it may point, so the vault is split
  by that and nothing else** — `client-patched/` + `run/` are ours and loopback-only,
  `client-patched-live/` + `run-live/` are ArenaNet's and live-only. Never select a
  build by filename: `sorted(exes)[-1]` picked the wrong one the day both configurations
  first existed. `toolkit/clientpatch/dhbuild.py` reads the struct and answers
  `ours`/`stock`/`unknown`, the patcher refuses to write either kind into the other's
  directory, and `python toolkit/clientpatch/dhbuild.py` audits the whole vault.
- **Never patch or launch anything under `C:\gw`.** That install is the owner's, and
  reading bytes from it is read-only.
- **Live automation against ArenaNet is authorized — on the secondary account, as a mode
  you enter deliberately.** Owner's decision, 2026-08-06 (`PLAN.md` §7 Q4). It is *not*
  the go-to test mode: the default loop is hand-driven against our own server, and live
  runs are for a capture campaign. The behavioural rule is the control that matters —
  human cadence, human hours, one client, never in a competitive context — because what
  closes accounts is a traffic pattern no person could produce — and no guard in this repo
  can substitute for that one. **All five preconditions in `PLAN.md` §6.2 are met as of
  2026-08-07**: the unpatched-DH build exists and is reproducible
  (`make_custom_client.py --no-dh-patch`), and its run directory is assembled at
  `vault/run-live/` and verified byte-identical to the source. **The driver exists as of
  2026-08-07** (`toolkit/harness/livesession.py`), the whole pipeline is proven end to end
  on loopback (`dryrun_keycapture.py`, elevated, green), and the live build is key-tapped
  and staged. What has not happened is the run, and it is human-driven on purpose: the
  driver launches, sniffs and taps, and sends **no** keystrokes or clicks — the operator
  logs in and plays, because the scripted input the loopback harness uses is precisely the
  traffic pattern the rule above is about. `RUNBOOK.md` §"Capturing a live session" is the
  procedure; do not pass `--host` (it is refused, and why is worth reading).
  **The launch rule is no longer "is it caged".** It is a binding, enforced from the
  bytes by `toolkit/clientpatch/dhbuild.py` and `cage.assert_launch_safe(exe, host)`: a
  client may only be launched at the server whose Diffie-Hellman exponent matches the
  parameters it carries. `ours`→loopback needs a verified cage; `ours`→live is refused
  (Stage A completes with the autofilled credential before the patch matters);
  `stock`→loopback is refused; `stock`→live is the authorized run and must **not** be
  caged. Never infer this from a filename, a directory or a flag — every other property
  of the two builds is identical, and on 2026-08-06 a stock build filed under a name
  that sorts last was picked by two tools as "the patched client". The other controls
  stand: every launch names its account (`toolkit/harness/accounts.py` — loopback uses a
  synthetic credential, and the automation flag is opt-in so the primary is refused by
  default), uncaging costs a UAC prompt, and every capture records whose server produced
  it (`toolkit/origin.py`, three-valued: ours, live, unknown — and a consumer that pools
  them refuses to mix).
- **Local and personal only.** No public shard, no PRs against upstream client-side
  projects on this project's behalf.
- **Other people's work is a second gate, and it is not the provenance gate.** Before a
  module takes an algorithm, a layout or a constant table from any upstream, add its row
  to `PLAN.md` §6.1's derivation register *first*, and credit it in
  [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) if its licence asks. Where an upstream
  grants nothing — `gw-preservation/*`, `Py4GW_Reforged` — the only permitted use is
  verifying a value we derived ourselves, and `toolkit/content.py` refuses to load a
  content row that cites one without recording what we checked it against. This rule was
  in `PLAN.md` §1.1 for two days while `gwdat.py` sat in the server's dependency chain
  breaking it; a rule nothing checks is a wish.

## How we decide what is true

The wins in this repo all came from capturing the client and reading it, never from
reasoning about it. Two of the three hardest questions so far were settled that way
*against* what the written sources claimed.

- **Verbatim-first.** Real bytes → replicate ONE piece → verify. Offline agreement
  between two of our own components proves nothing.
- **Label every claim.** The vocabulary is defined in
  [studies/character/FINDINGS.md](studies/character/FINDINGS.md): OBSERVED, UPSTREAM,
  RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND. Use it in study
  docs *and* at the call site. "OpenTyria says so" is UPSTREAM, not a fact about
  retail Guild Wars — and `schema/messages.json` was imported from OpenTyria, so the
  two agreeing is one witness counted twice.
- **Refuse to guess.** An unknown opcode stops the framer loudly (`Undecodable`); it
  does not get invented past. Same for a snapshot that could not read every file.
- **A probe states its prediction first.** `toolkit/authsrv/probes.py` — question,
  prediction, what to watch — because a probe with no stated expectation can be
  rationalised into agreeing with anything afterwards.
- **A check that cannot fail is not a check.** Prefer assertions the artifact can
  refute (the FFNA chunk walk closing to the exact byte; struct offsets landing where
  the source's own field names say they do) over ones our decoder forces true.
- **One change per test**, and commit at tested milestones with a real message.

## Working in this repo

- Windows, PowerShell. `python …` lines work in any shell; `.ps1` needs a leading `&`.
- **One branch and one worktree per session, and WORK IN IT.** Parallel arcs get a
  worktree under `.claude/worktrees/`; `C:\gd\Rurik` is `main` and is where arcs land,
  not where they are written. Half of `main`'s history is merge commits, so this is the
  repo's pattern rather than a new rule — what it needs is following. Merge when the arc
  lands, and don't leave it: **`PLAN.md` §3 is the single status authority and lives on
  `main`**, so an unmerged branch means §3 is stale for everyone else, which is the exact
  failure the top of this file is about.
- **First, establish which tree you are actually in.** Not which one you meant to be in.

  ```bash
  git rev-parse --show-toplevel
  ```

  Trees are not copies of each other and the drift is not small: on 2026-08-11 the
  packet-arc worktree was **33 commits and 42 `toolkit/` files** behind `main`, missing
  `cmsgstream.py`, `agentprobe.py` and `itemprobe.py` outright. A relative
  `python toolkit/…` runs **that tree's** copy, so a stale tree does not error — it
  returns a confident number from an old scanner. Working in one tree while committing
  to another is how that happens, and it is what happened that day: the branch existed
  and went unused for twenty commits while the shell sat in its worktree. If you do work
  across trees anyway, say so out loud, because the worktree's name will imply otherwise
  for the rest of the session. (The vault is *not* a reason to avoid a worktree —
  `toolkit/vaultpath.py` resolves it correctly from inside one. Never `../../vault`.)
- **Pin subagents to THIS session's tree — not to `main` — and make them prove it.**
  A subagent inherits the session's cwd, and under the rule above that inheritance is
  *correct*; the danger is a prompt that overrides it with the wrong absolute path.
  Naming a tree in prose does not move the shell either way: on 2026-08-11 two of five
  workflow agents read the stale worktree while being told they were in `C:\gd\Rurik`,
  and one skeptic's refutation rested on a file that does not exist in the tree it read.
  So resolve the tree once with the command above, hand agents **that** path, require
  every command to begin `cd <tree> &&`, show the tool examples that way rather than as
  bare relative paths, and have each agent re-run the check **first** and refuse on a
  wrong answer. Same principle as `vaultpath.require_dir()` — a fixture that silently
  resolves to the wrong thing turns every assertion behind it into a no-op. For
  read-only fan-out, `isolation: "worktree"` gives each agent a fresh tree at current
  HEAD and sidesteps the question.
- **Python 3, standard library only.** No third-party dependencies anywhere in
  `toolkit/`. Keep it that way — with three named carve-outs, and **read carve-out
  (3) before concluding that anything here is forbidden**, because this rule's
  first sentence has already caused a route to be scored impossible when it was
  merely expensive.
  **(1) 2026-08-06: read-only client analysis may use `capstone` and `pefile`**,
  because there is no reasonable stdlib x86 disassembler. It covers exactly
  `toolkit/clientscan/msghandler.py` and `toolkit/clientscan/codescan.py`.
  Nothing on the server path, and no tool whose byte patterns are fixed
  (`asserts.py`, `msgshape.py`, `areatable.py`, `genericvalue.py`), may take
  the dependency — those must keep working on a bare machine. Prefer a stdlib
  checker for any *claim* even when a disassembler produced it.
  **(2) 2026-08-07: the live-capture driver may use a packet-capture backend**
  (WinDivert/`pydivert` or Npcap), because the outbound connection to ArenaNet
  cannot be seen any other way — `rawlisten` is loopback-only, `tcptable` is
  metadata-only, and the alternative was hooking the client (owner chose off-wire
  capture, route C, `studies/livekey/CAPTURE.md`). It is scoped to the live driver
  **only** — never the server path, never a bare-machine requirement, never a
  test in the suite above. `keytap.py` (the key reader) is pure `ctypes` and takes
  no dependency; only the ciphertext capture does. Pin the exact backend and its
  licence in `PLAN.md` §6.1's derivation register before importing it.
  **(3) 2026-08-12: a native C/C++ toolchain is permitted. Owner's ruling,
  `PLAN.md` §7 Q6 — "a compiler is a cost, not a blocker."** A hook DLL, an
  injected loader or a code-cave assembler is costed on its merits and is **not**
  refused on dependency grounds. This carve-out exists because the rule's opening
  sentence was doing the opposite: read cold, "standard library only" made native
  code look forbidden, so a client-side route that needed it would be scored
  BLOCKED rather than expensive — the same failure the provenance gate had, where
  four days of sessions refused what the rule never actually said. Three things it
  does **not** change, and they are the whole boundary: the **server path stays
  dependency-free**; the fixed-byte-pattern tools (`asserts.py`, `msgshape.py`,
  `areatable.py`, `genericvalue.py`) must keep working **on a bare machine**, which
  is why (1) was scoped to two named files rather than to "client analysis"; and
  the **second gate is untouched** — a native dependency is still somebody else's
  work and needs its §6.1 row and its licence settled before a line imports it.
  Prefer `ctypes` where it genuinely suffices, as economics rather than as a rule:
  `toolkit/harness/keytap.py` already does cross-process `ReadProcessMemory` with
  ASLR-correct module bases in pure `ctypes`, and where that generalises it buys a
  shorter loop with no compiler in the inner cycle. Where it does not, use the
  compiler without apology.
- Tests are plain scripts that print `[PASS]`/`[FAIL]` and exit non-zero. Run them
  before touching the game — a red test names the broken thing, the client says
  `Code=058` thirty seconds later and tells you nothing.

  ```bash
  python toolkit/authsrv/test_handshake.py
  ```

  Others: `toolkit/schema/test_codec.py` (codec vs. real captured bytes — and
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
  control that the ordering check fails on a reversed finally),
  `toolkit/portal/test_webgate.py`, `toolkit/mapdata/test_archive.py`,
  `toolkit/mapdata/test_datcrc.py` (the archive's checksum and allocator rules),
  `toolkit/mapdata/test_datwrite.py` (the only tool that opens the archive `r+b`,
  against a small archive the test builds: that `--verify --replace` actually
  mutates rather than verifying and returning, that a shrinking replace journals
  its whole block reservation and zeroes the freed tail, that revert restores
  byte-for-byte even after something else took the freed blocks, and that the
  reservation refusal holds from both sides. Four defects, none of which could
  fail a checksum -- the archive verified perfectly through all of them),
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
  crash as "the row moved"),
  `toolkit/mapdata/test_atex.py` (the ATEX texture container, and first the write
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
  synthetic literal plus both maps' oracle and rival. Three scores, each
  MEASURED rather than subtracted, because the file needs TWO vault artifacts
  that fail independently: 57 with archive + client image, 33 with the client
  image alone, **29 with neither** -- against a floor of 57. ~121 s),
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
  with 0 overlapping pairs afterwards on the real 4.2 GB archive. What is still
  unmeasured is DURABILITY across a play session),
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
  passed against the defect),
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
  impostor archive of `test_mapfile`'s section 2b reddens at 1. Sections 0-4b need no
  vault and score 84 against a floor of 145, so a vault-less run goes red. ~48 s, and
  145 of 145 on BOTH vaulted archives, MEASURED 2026-08-13),
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
  must import the terrain alone. Sections 0-2
  need no vault and score 45 against a floor of 92. ~25 s),
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
  stamp and is genuine ambiguity. Sections 0-4
  need no vault and score 67 against a floor of 79. ~49 s),
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
  `toolkit/authsrv/test_spawn_burst.py`, `toolkit/authsrv/test_movement_fidelity.py`,
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
  `DROPPED_ON_PURPOSE`, six rows each carrying its reason -- 194 layouts against
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
  from nothing. 33 checks, ~2 s),
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
  **unsendable by this server until the `string16` fix**),
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
  `toolkit/clientscan/test_skillcast.py`, `toolkit/clientscan/test_textrec.py`,
  `toolkit/clientscan/test_srctree.py` (the Cli/Srv source-tree split, on both
  vaulted builds — and it proves its own negative result can go red first),
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
  `FF FF FF FF` is the fourteenth ELEMENT of the array and `arrsize` counts it, so
  14 x 4 lands on the anchor. What sentinels really cause is a third shape, a table
  whose left neighbour is not a string at all, which is why `s_skill`,
  `s_missionClientData` and `s_attribPoints` declare no left edge. **The headline is
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
  `s_eula` [4, 36, 44, 132]) and `s_worldData`'s stride is labelled UNSETTLED. That is
  not hypothetical: `s_glow` was entered in this corpus as 2 x 44, CLOSED on the
  correct base with a plausible record, and is 11 x 8. Three sabotages built and run
  and three redden -- a first-hit anchor, a +/- 4 pad tolerance, and the code witness
  dropped -- which is why `pad` is a declared exact number and never a tolerance
  (4 bytes is a whole record for the eight stride-4 tables here). It is also the
  first `source = "client-table"` extraction in this repo's history: `--emit-effect`
  writes all **2,077** `s_effect` rows with provenance per row, keyed by the ARRAY
  INDEX rather than the id column (one record's id is not its index, and keying by id
  would drop row 2036 and mint a 2077), and the test loads them through `content.py`
  and then REMOVES the build from one row and requires the load to FAIL, so the 2,077
  are proved to have passed condition 2 rather than skipped it. Sections 0-4 build a
  small PE32 image byte by byte and need no vault, scoring 28 against a floor of 61,
  so a vault-less run goes red. ~15 s),
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
  is a green run over nothing, which is this repo's oldest defect. No vault, no
  socket, no client; both halves are pure functions over a string and a tree, so
  testing the thing that spawns 76 processes spawns none. 27 checks, ~2 s),
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
  only claim about the real store is that its census carries no value out of it. 47
  checks against a floor of 45, the two vault-dependent ones declaring a skip. ~3m25s),
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
  matched. The POSITIVE CONTROL is what earns the file and it is not synthetic:
  `vault/run-live/`, a copy a client really played live from, genuinely does not
  bind `0x8001B97D`, and the check must go FATAL on EXACTLY the two Pre-Searing
  rows while the other eight stay green -- a guard that reddens on all ten says
  nothing. Identity is the MFT entry's size and crc, never the row, because row
  indices do not survive a patch; a one-bit crc mutation must be caught, since
  two archives resolving one id to different FILES is worse than a failed launch
  (the run produces data and looks like it worked). Section 4 asserts the
  LOOPBACK GATE on the syntax tree -- a live run answers to ArenaNet's own ids
  and must never be refused on our rows, and "the call is inside the RUN_ROOT
  branch" is invisible to a grep; the sabotage that removes the gate reddens it
  alone. ~3 s),
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
  ArenaNet's can never be pooled).

  **This list is the suite.** A test in the tree but not named here is a test
  nobody runs: `test_pathmap.py`, `test_skillcast.py` and `test_textrec.py` were
  each missing from it for days. Add the line in the same commit as the test.
  **And run all of it.** On 2026-08-06 this suite was reported green from a run of
  twenty of its twenty-three entries; both omitted tests were red, and one of them
  (`test_harness.py`) was red because `drive_client.py` could not be imported at all —
  so the launch sites had been broken for a day behind a green-looking report. A
  partial run reported as a full one is the same defect as a missing line, from the
  other side. Name the count when you report it.
- **A run that measured nothing failed.** Every test routes its verdict through
  `toolkit/checks.py`, and declares a `floor` — the number of checks a healthy run
  executes. Fewer than that, or none at all, is a FAIL naming the shortfall; a
  section that cannot run declares `LEDGER.skip(...)` and is printed, never
  silent. This exists because it happened twice: `test_codec.py` printed ALL
  CHECKS PASSED with its fixture glob matching nothing, and
  `test_movement_fidelity.py` printed it while skipping a whole section and
  scoring its headline number over n=2. Set the floor from a real green run, never
  from a guess, and never above what one produces. `toolkit/test_checks.py` breaks
  each rule on purpose to prove the guard can go red.
- **Find the vault with `toolkit/vaultpath.py`, never with `../../vault`.** A git
  worktree has no vault of its own, so a relative walk lands on nothing — and a
  fixture that resolves to nothing turns every assertion behind it into a no-op.
  `require_dir()` raises instead. Override with `RURIK_VAULT` if the vault moves.
- The daily three-terminal loop, the one-time client patching, and the failure table
  are in [RUNBOOK.md](RUNBOOK.md). The DH parameters rotate with every client build,
  so an ArenaNet update means redoing that setup in full.
- Research lives in `studies/<arc>/` as `FINDINGS.md` or `PLAN.md`, labelled per
  above, and outlives the session that produced it. Fan recon out to Sonnet agents;
  keep judgement calls on Opus/Fable.

## Layout

| Path | What it is |
|---|---|
| `toolkit/portal/`, `toolkit/authsrv/` | The server: portal (6601), auth + ARC4 channel (6112) |
| `toolkit/schema/` | Codec and the message-catalog importer |
| `schema/messages.json`, `overrides.json` | The wire schema, tracked in git |
| `content/*.toml` | The world: maps, NPCs, items, spawns. One row per fact, each carrying its own provenance. Loaded by `toolkit/content.py`; the server holds no content literals. Bulk extraction goes to `vault/content/` and is merged over these. |
| `toolkit/clientscan/`, `toolkit/clientpatch/` | Read-only client analysis; patching and the firewall cage |
| `toolkit/mapdata/` | `Gw.dat` reader, planner (`datplan`), writer (`datwrite`), textures (`atex`, `dxt1`) |
| `studies/` | Per-arc research, labelled by confidence |
| `vault/` | Gitignored. Snapshots, keys, captures, prior-art mirrors. Client builds are filed by whose DH they carry: `client-patched/`+`run/` ours, loopback-only; `client-patched-live/`+`run-live/` stock, live-only |
