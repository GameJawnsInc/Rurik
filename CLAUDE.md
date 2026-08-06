# CLAUDE.md

Rurik is a private, local Guild Wars 1 server emulator plus a content toolkit. The
strategy is in [HANDOFF.md](HANDOFF.md), the corrected mechanism and the ladder in
[PLAN.md](PLAN.md), and every operational procedure in [RUNBOOK.md](RUNBOOK.md).
Read those rather than re-deriving them here. This file is the house rules.

Current edge: R1 is done (a real client reaches character select and a body stands
in a map); R2 is the game server. `PLAN.md` §8 is the live list.

## Non-negotiable

- **Provenance gate: zero ArenaNet bytes in the repo, ever.** No client files, no
  `Gw.dat`, no extracted assets, no decompiled code — only our code and our
  observations. The rationale is at the top of `.gitignore`; read it before editing
  that file. Retrofitting provenance is not possible.
- **The vault stays local.** `vault/` holds captures, keys and client snapshots. It
  is gitignored, it is personal data from the owner's own account, and it never goes
  on the internet. Probe output goes there too.
- **Never point a patched client at the real service**, and never patch or launch
  anything under `C:\gw`. That install is the owner's, and reading bytes from it is
  read-only. Live probes against ArenaNet need an explicit go-ahead from the owner.
- **Local and personal only.** No public shard, no PRs against upstream client-side
  projects on this project's behalf.

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
  `toolkit/`. Keep it that way — with one named carve-out, decided 2026-08-06:
  **read-only client analysis may use `capstone` and `pefile`**, because there
  is no reasonable stdlib x86 disassembler. It covers exactly
  `toolkit/clientscan/msghandler.py` and `toolkit/clientscan/codescan.py`.
  Nothing on the server path, and no tool whose byte patterns are fixed
  (`asserts.py`, `msgshape.py`, `areatable.py`, `genericvalue.py`), may take
  the dependency — those must keep working on a bare machine. Prefer a stdlib
  checker for any *claim* even when a disassembler produced it.
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
  `toolkit/mapdata/test_gwdat.py` (the decompressor, including zero-length codes),
  `toolkit/mapdata/test_pathmap.py` (trapezoid walk, A* and line of sight),
  `toolkit/authsrv/test_spawn_burst.py`, `toolkit/authsrv/test_movement_fidelity.py`,
  `toolkit/clientscan/test_skilltable.py` (client skill rows vs. the wiki),
  `toolkit/clientscan/test_areatable.py` (the map table and string-id decoding),
  `toolkit/clientscan/test_skillcast.py`, `toolkit/clientscan/test_textrec.py`,
  `toolkit/clientscan/test_srctree.py` (the Cli/Srv source-tree split, on both
  vaulted builds — and it proves its own negative result can go red first),
  `toolkit/clientscan/test_codescan.py` (the attack-speed chain, and the two
  decoding traps that hid it — needs capstone),
  `toolkit/test_checks.py` (the check on the checker — see below),
  `toolkit/test_scrub.py` (the credential scrub, and that no secret survives it).

  **This list is the suite.** A test in the tree but not named here is a test
  nobody runs: `test_pathmap.py`, `test_skillcast.py` and `test_textrec.py` were
  each missing from it for days. Add the line in the same commit as the test.
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
| `toolkit/clientscan/`, `toolkit/clientpatch/` | Read-only client analysis; patching and the firewall cage |
| `toolkit/mapdata/` | `Gw.dat` reader, planner (`datplan`), writer (`datwrite`), textures (`atex`, `dxt1`) |
| `studies/` | Per-arc research, labelled by confidence |
| `vault/` | Gitignored. Snapshots, keys, captures, prior-art mirrors |
