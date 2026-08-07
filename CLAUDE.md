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
  `vault/run-live/` and verified byte-identical to the source. What is missing is the
  driver — no tool yet knows how to run a capture session — which is R0b's own first
  commit, not a gate to be opened.
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
  `toolkit/test_scrub.py` (the credential scrub, and that no secret survives it),
  `toolkit/test_content.py` (the content store, and that its provenance and licence
  refusals actually refuse),
  `toolkit/clientpatch/test_cage.py` (the launch gate: which binary may be aimed at
  which server, both directions — slow, ~1 min, it queries the Windows Firewall once
  per client),
  `toolkit/clientpatch/test_dhbuild.py` (whose DH a build carries, that hostile
  filename order can no longer pick the wrong one, and that a build cannot be
  assembled into the directory meant for the other kind),
  `toolkit/harness/test_accounts.py` (the account selector, and that the primary is
  refused),
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
