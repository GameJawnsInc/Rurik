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
  `make_custom_client.py` applies, only the DH substitution disqualifies a client, and
  the multi-instance NOP is wanted on both configurations. **The updater kill switch is
  NOT** — this sentence used to say it was, and on 2026-08-14 somebody followed
  `RUNBOOK.md`'s setup steps literally and built a live-capture client that could not
  stream map content. The kill switch is **wanted on the loopback build** (the cage and
  the pre-login patcher are in direct conflict, so with the updater dead the cage never
  has to open) and **must be OFF for the live-capture build**, which needs to fetch
  content during a real session — `RUNBOOK.md` §"a live run writes new content into its
  own `Gw.dat`". Build it with `--no-dh-patch --no-updater-patch --key-tap`; expect
  `updater=LIVE` for everything under `run-live/` and `updater=killed` under `run/`,
  and check with `python toolkit/clientpatch/dhbuild.py`.
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
  and staged. **The run itself is human-driven by design**: the driver launches, sniffs
  and taps, and sends **no** keystrokes or clicks — the operator logs in and plays,
  because the scripted input the loopback harness uses is precisely the traffic pattern
  the rule above is about. (This paragraph used to end "what has not happened is the
  run", written 2026-08-07 12:41 and still saying it a week later — the run landed at
  14:30 **that same day** and six live captures sit in the vault. Status of the live
  campaign is `PLAN.md` §3's R0b row and nowhere else; that is what the top of this file
  is about, and this sentence is the file breaking its own rule for seven days.) `RUNBOOK.md` §"Capturing a live session" is the
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

  The catalog of every test and what it is really checking lives in
  **[TESTS.md](TESTS.md)** — it is 2,400+ lines and it was 90% of this file until
  2026-08-14. Read it when you touch a module; do not read it to run the suite.

  **That file is the suite.** A test in the tree but not named in `TESTS.md` is a
  test nobody runs: `test_pathmap.py`, `test_skillcast.py` and `test_textrec.py` were
  each missing from it for days. Add the entry in the same commit as the test —
  `test_srclint.py` §7 checks both directions and can go red.
  **And run all of it**, with `python toolkit/run_suite.py`, which discovers tests
  from the DISK and never from either document.
  On 2026-08-06 this suite was reported green from a run of
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
| `schema/messages.json`, `schema/overrides.json` | The wire schema, tracked in git |
| `content/*.toml` | The world: maps, NPCs, items, spawns. One row per fact, each carrying its own provenance. Loaded by `toolkit/content.py`; the server holds no content literals. Bulk extraction goes to `vault/content/` and is merged over these. |
| `toolkit/clientscan/`, `toolkit/clientpatch/` | Read-only client analysis; patching and the firewall cage |
| `toolkit/mapdata/` | `Gw.dat` reader, planner (`datplan`), writer (`datwrite`), textures (`atex`, `dxt1`) |
| `studies/` | Per-arc research, labelled by confidence |
| `vault/` | Gitignored. Snapshots, keys, captures, prior-art mirrors. Client builds are filed by whose DH they carry: `client-patched/`+`run/` ours, loopback-only; `client-patched-live/`+`run-live/` stock, live-only |
