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
  `Gw.dat`, no extracted assets, no decompiled code — only our code and our
  observations. The rationale is at the top of `.gitignore`; read it before editing
  that file. Retrofitting provenance is not possible.
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

  Others: `toolkit/schema/test_codec.py` (codec vs. real captured bytes),
  `toolkit/schema/test_catalog.py` (our message catalog vs. the client's own
  format tables — 477/477 GAME_SMSG agree field-for-field on build 38797),
  `toolkit/harness/test_harness.py` (the one-command stack, the launch safety
  gate, the live capture tail),
  `toolkit/portal/test_webgate.py`, `toolkit/mapdata/test_archive.py`,
  `toolkit/mapdata/test_datcrc.py` (the archive's checksum and allocator rules),
  `toolkit/mapdata/test_datwrite.py` (the only tool that opens the archive `r+b`,
  against a small archive the test builds: that `--verify --replace` actually
  mutates rather than verifying and returning, that a shrinking replace journals
  its whole block reservation and zeroes the freed tail, that revert restores
  byte-for-byte even after something else took the freed blocks, and that the
  reservation refusal holds from both sides. Four defects, none of which could
  fail a checksum -- the archive verified perfectly through all of them),
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
  `toolkit/authsrv/test_spawn_burst.py`, `toolkit/authsrv/test_movement_fidelity.py`,
  `toolkit/authsrv/test_agentlife.py` (WORLD_REMOVE_AGENT and its two refusals,
  and that an unframeable opcode stops the framer instead of being framed past),
  `toolkit/authsrv/test_tape.py` (R1.5's tape loader: the events ARE the recorded
  stream whole and in order, and a tape whose wire bytes do not account for the
  plaintext -- or that came from our own server -- is refused),
  `toolkit/authsrv/test_labelrun.py` (the labelled input run, which names GAME_CMSG
  opcodes from what a human was told to do: a message lands in exactly one step's
  window, instance-load traffic is never folded into step 1, and a dirty idle CONTROL
  is reported and exits non-zero rather than letting a misattributed opcode be named),
  `toolkit/authsrv/test_burrow.py` (burrowing, in two halves kept apart: ArenaNet's own
  bytes re-measured from the capture — 140 worm re-creations, ONE burst shape, the two
  2.00 s transition windows — and our own cycle driven with a fake `send`. It exists
  because the study doc was wrong: T3 said burrowing "runs entirely through the two
  opcodes we already implement" and it is five messages, so a test that asserted the
  doc would have locked the error in),
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
  `toolkit/clientscan/test_skilltable.py` (client skill rows vs. the wiki),
  `toolkit/clientscan/test_areatable.py` (the map table and string-id decoding),
  `toolkit/clientscan/test_skillcast.py`, `toolkit/clientscan/test_textrec.py`,
  `toolkit/clientscan/test_srctree.py` (the Cli/Srv source-tree split, on both
  vaulted builds — and it proves its own negative result can go red first),
  `toolkit/clientscan/test_codescan.py` (the attack-speed chain, and the two
  decoding traps that hid it — needs capstone),
  `toolkit/test_checks.py` (the check on the checker — see below),
  `toolkit/test_srclint.py` (every `toolkit/` file, for a name a function reads that
  nothing could have bound: `ast.parse` and the whole suite passed a `NameError` into
  a live session on 2026-08-10. It also pins the checker's own vacuity failure — the
  first version treated every function local as a module binding and scored the real
  defect zero),
  `toolkit/test_scrub.py` (the credential scrub, that no secret survives it, that the
  one field it CANNOT clean — a `plain` frame payload, which carries the account email as
  UTF-16 and is therefore invisible to the ASCII leak check — is reported rather than
  silently passed through, and that its record arithmetic is pinned to a snapshot so a
  live server appending to `vault/captures/` cannot make it disagree with itself),
  `toolkit/test_content.py` (the content store, and that its provenance and licence
  refusals actually refuse),
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
