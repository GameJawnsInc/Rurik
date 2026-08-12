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
    audio, model data, decompiled bodies, and **verbatim assert expressions with their
    source path and line**. A derived table may carry the *constraint* (opcode, field,
    bound, address) and must leave the expression text out.
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
  `toolkit/`. Keep it that way — with two named carve-outs.
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
  `held 8.0s of 8.0s` six times. Only the capture could tell the two apart),
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
  go red ALONE, because a gate that reddens at everything is as useless as one
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
  `toolkit/mapdata/test_pathmap.py` (trapezoid walk, A* and line of sight),
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
  `toolkit/mapdata/test_mapexport.py` (the neutral terrain interchange, and the
  orientation checked against a chunk the exporter never reads: prop `z` from
  `0x20000004` sampled against the exported height field, with three rival layouts
  that must collapse — on Kamadan the fraction of props within 100 units is 0.304
  against 0.070 for the y-flip, 0.033 for the x-flip and **0.085 for not de-tiling
  at all**, which reproduces FINDINGS §4's 0.089 for the flat row-major rival from
  the other side; Pre-Searing is 0.734 against 0.078/0.139/0.137. Kamadan sits below
  FINDINGS' 0.504 corpus median and is reported at its real value rather than
  dropped. Every prop of both maps lands inside the grid under all four layouts, so
  no control loses on sample size. Also: `detile` checked cell-for-cell against
  `terrain.Terrain.index`, a different implementation in a module this rung does not
  own; a sha256 manifest whose negative control flips one mantissa bit of one height
  and must be caught; and a refusal that keeps derived ArenaNet bytes out of the
  working tree — which shipped broken, one `dirname` short, and wrote a 745 KB height
  field into the repo before the test pinned the resolved root. Sections 0-4 need no
  vault and score 65 against a floor of 108, so a vault-less run goes red. ~31 s),
  `toolkit/mapdata/test_blenderimport.py` (the Blender half: it runs
  `tools/blender/import_gwmap.py` headless as a SUBPROCESS — the test is stdlib-only
  and never imports `bpy`, which is why the importer may live outside `toolkit/` —
  and checks the mesh Blender actually built. 213,921 vertices and 212,992 quads for
  Pre-Searing, every face a quad, every normal +Z, and the bounding box equal to the
  Map Parameters rect to the bit. The oracle is again a chunk neither tool reads:
  prop `z` looked up in Blender's own vertex buffer **by world coordinate rather than
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
  run that asked for one Blender measured another and printed green. Sections 0-2
  need no vault and score 39 against a floor of 75. ~13 s),
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
  into a map file that passes all 17 of the client's open-time gates. Sections 0-4
  need no vault and score 65 against a floor of 77. ~39 s),
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
  `--all` is ~13 minutes),
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
  found false (276 is elite), the comment having been the only witness),
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
  the exact silence D9(a) is about. No vault, no socket, no client),
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
  12 canon connections),
  Section 7b covers `sweeploop.py`, the unattended driver: its stop conditions are a
  PURE function so they can be checked without a client, and its control is that ONE
  barren round must NOT stop -- a single unlocalised crash is normal, and stopping at one
  would end most sweeps early. The last check asks the SYNTAX TREE whether the loop
  imports the cage or launches anything itself, because the grep version of that check
  went red on the docstring explaining the rule),
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
  `toolkit/clientscan/test_skilltable.py` (client skill rows vs. the wiki),
  `toolkit/clientscan/test_areatable.py` (the map table and string-id decoding),
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
  noise),
  `toolkit/test_checks.py` (the check on the checker — see below),
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
  live server appending to `vault/captures/` cannot make it disagree with itself),
  `toolkit/test_content.py` (the content store, and that its provenance and licence
  refusals actually refuse),
  `toolkit/test_provlint.py` (an ACCUMULATION TRIPWIRE on assert citations in prose,
  and the story of why it is only that is worth more than the file. `content.py`
  enforced the provenance gate's permitted side from the day it was written; the same
  ruling's refusal of "verbatim assert expressions with their source path and line"
  applied to prose and was checked by nobody, so 134 citations sat in sixteen docs.
  Read literally that made all 134 refusable, and 46 were scrubbed before the owner
  asked whether provenance was starting to cost more than it protected. **It was**,
  and `PLAN.md` §7 Q3 was refined the same day: **a single assert cited as evidence is
  a MEASUREMENT; the refusal targets BULK dumps and decompiled bodies**, and the crash
  dialog — text the retail client shows any player who crashes — is not extraction.
  This repo's recorded provenance mistakes are REFUSALS, not disclosures. So the 104
  remaining are permitted, `smsg` keeps the 65 quotes that make its opcode naming
  auditable, and the test allows it 80 while an unlisted doc gets 10. The ceiling was
  checked in the direction that matters: a 15-row dump appended to a document that
  argues from none trips it. **The lesson to carry, not the code:** a rule read at
  maximum strictness generated a session of rewrites against negligible risk, and the
  cheap part — a tripwire with real headroom — was the only part worth keeping. There
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
  `toolkit/harness/test_accounts.py` (the account selector, and that the primary is
  refused),
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
