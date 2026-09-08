# Runbook — driving the real client against Rurik

Copy-pasteable from `C:\gd\Rurik` **in PowerShell**, the shell this project is
driven from. Every `python …` line works unchanged in PowerShell, `cmd.exe` and
bash alike; the one shell-sensitive line is launching the client, which needs a
leading `&` (step 3).

**Where the project is: [PLAN.md](PLAN.md) §3.** This runbook deliberately does not
say — it used to, and it was wrong for 40 hours while asserting that clicking *Play*
was unimplemented, long after a body was standing in a map and walking into walls.
A procedure document that also claims to know the state of play will drift from it,
and this is the first file a cold session opens.

What this file is for: driving the real client against the stack, whatever rung the
stack is on.

---

## TL;DR — the daily loop

One command, once the one-time setup below has been done:

```bash
python toolkit/harness/session.py
```

It pre-flights the ports (a stale listener is named by pid and image;
`--replace` stops it if it is a python server, and refuses to touch anything
else), starts all three servers and proves each owns its port, drives the
client through login → EULA → Play with focus-verified clicks, and judges the
run from the client's own messages — one `[PASS]`/`[FAIL]` line per checkpoint,
ending at the spawn request. `--until login` stops sooner, `--serve` runs just
the stack in one terminal, and the report, server logs and screenshots land in
`vault/captures/harness/<stamp>/`. The harness's own offline tests:

```bash
python toolkit/harness/test_harness.py
```

Two things it knows that the terminals below do not say:

- The game channel is served by a **second authsrv.py instance** — the client
  declares its channel in its version header, so the same code decodes the game
  catalog with no extra flag.
- OBSERVED build 38797 (2026-08-06, handshake PLAN §10): the client dials the
  GAME_SERVER_INFO **host** at hardcoded port **6112**; the advertised port is
  decorative. The stack therefore gives the game catalog a loopback alias of
  its own: the handoff advertises `127.0.0.3`, the gamesrv listens on
  `127.0.0.3:6112`, and game traffic records to `vault/captures/gamesrv/`
  instead of mixing into the auth capture. The harness's map checkpoints watch
  only that dir, so a handoff pointing back at the auth host fails loudly.

### The same loop by hand

Four terminals, in this order. Nothing here needs admin except the client.

```bash
python toolkit/portal/webgate.py
```

```bash
python toolkit/authsrv/authsrv.py --game-host 127.0.0.3
```

```bash
python toolkit/authsrv/authsrv.py --bind 127.0.0.3 --port 6112 --vault vault/captures/gamesrv
```

(That third terminal is the game catalog. Without it — or with the handoff left
at its `127.0.0.1` default — the game dial lands back on the auth listener,
whose catalog self-selection still serves the game but records it into
`vault/captures/authsrv/`, mixed with auth traffic.)

Terminal 4 is the client. Launch the exe directly — **no elevation, and not
`launch_caged.ps1`**:

```bash
& "C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe" -authsrv 127.0.0.1 -portal 127.0.0.1 -windowed -log
```

This step used to route through `launch_caged.ps1`, which drops the firewall
block rule, walks the client past its pre-login patcher, and re-cages in a
`finally`. That was necessary once: the patcher needs one outbound check before
it shows the login screen, the block denies it instantly and forever, and the
client sits on *Connecting to ArenaNet* with no socket to explain why.

**It is no longer necessary, and it was never safe.** Firewall rules are
evaluated at connection **establishment**, and Windows offers no supported way to
tear down an established TCP connection — so anything opened inside the window
outlives the re-cage for the life of the process. The updater kill switch
`make_custom_client.py` applies by default removes the need entirely: with the
updater off the patcher never runs, so the cage never has to open. That fix
shipped and this page went on naming the script for weeks afterwards. It now
refuses any build carrying the kill switch; check yours with

```bash
python toolkit/clientpatch/dhbuild.py
```

Then log in at the client's own screen with **any** account name and password —
the webgate authenticates nobody by design. Accept the User Agreement if it
appears; that is client-side UI and accepting it sends three bytes to loopback.

Afterwards, see what the client said:

```bash
python toolkit/authsrv/summarize_capture.py
```

---

## Before that: check it works without the game

Always. A red test names the broken thing; the game says `Connecting…` for thirty
seconds and then `Code=058`, which tells you nothing.

**The whole suite is one command**, and it is the only way to report a count you can
trust — `CLAUDE.md`'s rule is *run all of it and name the count*, and every "the suite
is green" in this repo's history before 2026-08-13 was a human pasting paths into a
shell:

```bash
python toolkit/run_suite.py
```

One process per file, discovered from **the disk** rather than from any document, and
`rc == 0` with no `ALL CHECKS PASSED` banner is reported `SUSPECT` rather than laundered
into a pass. `--only <substring>` filters, `--list` enumerates and stops.

**It runs four files at a time, longest-first.** Baseline 2026-08-15, 96 files:
**621 s wall — 10.4 minutes, down from 46.6 serial.** `--jobs 1` restores one-at-a-time
and is how you check a suspected collision: a parallel run that disagrees with a serial
one about any file's verdict is a collision, not a flake.

**Four is measured, not guessed, and raising it will not help.** Wall clock is flat from
4 to 8 workers — 621 s, 595 s, 623 s — while the summed cost of the same 96 files goes
2,484 s → 3,498 s → 4,196 s. Eight workers spend 1,700 CPU-seconds fighting for the disk
and finish no sooner (`test_scrub` reads 270 s at four jobs and 457 s at eight, for
identical work). All three runs agreed on every verdict and every check count. This box
feeds about four concurrent heavy readers, so **the only way below ~10 minutes is
removing work, not adding workers.**

Where the remaining time is, if you go looking: `test_modelexport` ~390 s and
`test_scrub` ~270 s at four jobs, then `trnshadow`, `pathmap`, `blenderroundtrip` and
`atexlevel`. Half the suite still finishes in under a minute put together. Both of the
former hogs were cut on 2026-08-15 — 584 s → 183 s and 480 s → ~330 s standalone — by
removing accidental work, with every assertion and every reported number unchanged; see
TESTS.md for `search_all` and `Archive.magic`.


### Once per clone: install the commit gate

```bash
git config core.hooksPath .githooks
```

**One line, and it is not optional now the repository is public.** It points git at
`.githooks/pre-commit`, which runs `toolkit/githooks/pre_commit.py` and refuses a
commit that stages a vault-shaped path or credential-shaped content — a capture, a
key, a binary, a real email address, a `C:\Users\<real name>` path, a character name
travelling as UTF-16 hex. It is per-clone because `core.hooksPath` is local
configuration: a fresh clone, a new worktree with its own config, or a machine you
have not run this on is **unguarded until you run it**. Check with
`git config core.hooksPath`, which must print `.githooks`.

**Why a hook and not just `.gitignore`:** the ignore rules cover the vault by
DIRECTORY, so a capture written into the checkout root — by a tool whose `--out`
defaulted there, or a copy made to look at something — is not ignored at all and
`git add -A` takes it. That was survivable while the repository was private. It is
not now: a push is a publication, and rewriting history afterwards does not remove
the objects from GitHub (`studies/prepub/FINDINGS.md` §8, which is why the remote
had to be deleted and re-created).

The gate prints what it refused and why, one line per finding with a line number
where it read content. If a refusal is wrong, `git commit --no-verify` is the
deliberate way through — that is the override CLAUDE.md's rule permits, since you
have read the refusal and decided, and it leaves the decision on the record. What
the rule forbids is skipping a red you have not read.

### While you are working: only what your edits reach

Ten minutes is still too long after every edit, so during the loop:

```bash
python toolkit/run_suite.py --since HEAD
```

Tests reachable from your changed modules, through a real dependency graph — imports
plus the subprocess launches an import graph cannot see. `--since main` covers
everything the branch touched.

**HOW MANY tests it picks does not tell you how long it takes, and the two run in
opposite directions here.** MEASURED 2026-08-15, at the default four jobs:

| a change to | selects | wall |
|---|---|---|
| `authsrv/authsrv.py` | 34 of 96 | **87 s** (measured) |
| `schema/codec.py` | 39 of 96 | ~105 s |
| `mapdata/dxt1.py` | **14 of 96** | **~390 s** |
| `mapdata/archive.py` | 68 of 96 | ~530 s |
| `checks.py` | 96 of 96 | the full suite |

Only the first is a stopwatch figure; the rest are its arithmetic — sum the selected
files' times, divide by four, floor at the longest single file — which came in 20%
HIGH on the one that was checked (105 s predicted, 87 s actual), so treat them as
budgets rather than promises.

The `dxt1.py` row is the one to remember. It selects the FEWEST tests of anything in
the table and costs four times what a change to the whole auth server costs, because
the fourteen it picks are the expensive texture and atlas files. A small blast radius
made of slow tests is slower than a wide one made of fast ones, so read the selection
list rather than its length.

Three behaviours worth knowing before you rely on it:

- **A green partial run exits 3, never 0**, and prints how many files never ran. That
  is deliberate: the banner protects a human reading a pasted report, the exit code
  protects a script. **`--only` exits 3 too** — it always was a partial run, and it
  returned 0 for as long as this runner existed. A failure still outranks it: red is
  1 whether or not the run was scoped.
- **A change to anything that is not `toolkit/**.py` forces the FULL suite** and says
  which file did it. `content/*.toml`, `schema/messages.json` and `CLAUDE.md` are read
  at run time by tests that never import them, so the graph is structurally blind to
  those edges and refuses to guess.
- **"0 tests selected" is not an all-clear.** Eleven modules in `toolkit/` have no test
  reachable from them at all — `rawlisten.py`, `flagscan.py`, `admin.py` among them —
  and a change confined to one of those exits 2 with a coverage statement.

Selection helps `mapdata/` least, and the table above says why: `archive.py` reaches 68
of the 96 files, so it lands at ~530 s against the full suite's 621 s — a scoped run
that saves about a minute and a half. That is a property of the code, not of the
selector: `archive.py` is what almost everything under `mapdata/` opens the world
through. Server, schema and portal work is where `--since` pays, and it pays well.

**`python toolkit/run_suite.py` with no flags is the suite. Nothing else is** — that is
the count you report, and `CLAUDE.md`'s rule is to name it.

**A red suite here is not always your change.** Several tests refuse to pool captures
from two client builds, so a capture landing in `vault/captures/authsrv|gamesrv/` from
ANOTHER session turns `test_origin`, `test_codec` and `test_movement_fidelity` red
without a line of code changing. That happened on 2026-08-14. Check
`python toolkit/test_origin.py` first: if it names two build ids, the vault drifted and
the other two are downstream of it, not of you.

Individual files, when you want one answer fast:

```bash
python toolkit/authsrv/test_handshake.py
```

Ends `HANDSHAKE VERIFIED`. It drives the entire login offline — key exchange,
computer info, portal login, and the five-message character burst — using a test
client that reads the DH parameters **out of the patched executable**, so the whole
chain is exercised. Its last check is a negative control: an unpatched client must
derive a *different* key.

```bash
python toolkit/portal/test_webgate.py     # portal endpoints
python toolkit/schema/test_codec.py       # wire codec, against real captured bytes
```

---

## One-time setup, and again after every ArenaNet update

The client auto-updates and **the Diffie-Hellman parameters rotate with every
build** — a patched copy from last week keys to nothing. Order matters: snapshot
*before* accepting an update, or you have already lost the build you were working
against.

### 0. Before you accept anything: capture the before-state

One command, and it is the whole of it. Run this the moment you see an update
prompt, before clicking anything.

```bash
python toolkit/updatecheck.py --before --snapshot
```

`--snapshot` copies `C:\gw` into the vault via `snapshot_client.py`; **without
it the command only reads**, which is safe any time but leaves out the one part
of the before-state that cannot be recovered afterwards. Exit **0** captured,
**2** the run could not be made — including exit 3 from the snapshot, meaning a
file is LOCKED and the copy is incomplete. Close the client and re-run; do not
accept the update on a 2.

It records every vaulted build's number, what the live install currently is, the
signature corpus with the addresses each anchor resolves to, the class-(a)
address census, the schema's build stamp, and the DH parameters **as a
fingerprint only** — never the values, which are ArenaNet key material. The
baseline goes to `vault/updatecheck/` and is refused into any checkout of this
repo.

### 0b. After the update: one page on what moved

```bash
python toolkit/updatecheck.py --after vault/updatecheck/before-<stamp>.json
```

Exit **0** nothing moved, **1 something did — which is a RESULT, not an error**,
**2** the run could not be made. The distinction is `datcheck.py`'s and it is not
decoration: conflating "it changed" with "it could not run" once cost a crash
being reported as a moved row.

The line worth reading first is the signature corpus. An anchor that moved to a
new address but kept its hit count **still resolves** and needs nothing; one whose
hit count changed is flagged `RE-DERIVE THIS`, and every tool that owns it is
untrustworthy until it is. Then work through the numbered steps below, which the
report will tell you are necessary.

**1. Confirm the crypto scheme is still where we think it is.** Reads
`C:\gw\Gw.exe`, touches nothing.

```bash
python toolkit/clientscan/dump_dh_params.py
```

Expect `generator g : 4`, a 512-bit prime, and a final `GO.` line.
If it says **NOT FOUND**, stop: the accessor signature changed, and no patching
tool in this repo or anyone else's can be trusted until it is re-derived. That is
a finding to write up in `studies/handshake/PLAN.md`, not a thing to work around.

**2. Snapshot the client.**

```bash
python toolkit/snapshot_client.py
```

Exit `0` means every file verified byte-identical; exit `3` means something was
locked — close Guild Wars and re-run. An incomplete snapshot is recorded as such
in the manifest so it cannot be mistaken for a complete one.

**3. Patch a copy and build a directory it can run from.**

```bash
python toolkit/clientpatch/make_custom_client.py
```

```bash
python toolkit/clientpatch/make_run_dir.py
```

The first writes a fresh DH triple into a **copy** (it refuses to write anywhere
under `C:\gw`), saves the private half to `vault/keys/rurik_dh_<build>.json`, and
ends with `B == g^b mod p -> True`. If that says `False`, do not launch the binary.
The second assembles `vault/run/<build>/` with the exe, `Gw.dat` and the DLLs
(~4.2 GB, a few seconds) and **prints the exact launch command** — use that, since
the path is build-specific.

**Keep the key file.** The server needs `server_private` to decrypt. Lose it and
the patched client is a brick.

**There are two client builds and they are not interchangeable.** The commands above
make the loopback one — our DH parameters — into `vault/client-patched/` and
`vault/run/`. The live-capture build is ArenaNet's own parameters, into
`vault/client-patched-live/` and `vault/run-live/`:

```bash
python toolkit/clientpatch/make_custom_client.py --no-dh-patch --no-updater-patch
```

```bash
python toolkit/clientpatch/make_run_dir.py --live
```

**`--no-updater-patch` is not optional and this line used to omit it**, which is a
documentation bug the 38833 update caught by making somebody follow the page
exactly. `make_custom_client.py` kills the updater **by default**, and that default
is right for the caged loopback build (§"Stuck on Connecting to ArenaNet" — the cage
and the pre-login patcher are in direct conflict) and **wrong for this one**: §"a
live run writes new content into its own `Gw.dat`" below is the same document
stating that `run-live/` must be able to stream map content. Following the old
wording produced a 38833 live build reading `updater=killed` beside a 38797 one
reading `updater=LIVE`, in a pair that is supposed to differ **only** in build.
Check with `dhbuild.py` and expect `updater=LIVE` for everything under
`run-live/` and `updater=killed` under `run/`. (`CLAUDE.md`'s launch-rule paragraph
used to say the kill switch was "wanted on both configurations", which contradicted
this page; **resolved 2026-08-14 in this page's favour** — the vault and the evidence
both agree with it, and `CLAUDE.md` now names the split explicitly.)

Never move a build between those directories and never pick one
by filename: the tools decide from the DH struct, and

```bash
python toolkit/clientpatch/dhbuild.py
```

says what every build in the vault is and whether it is where it belongs. **The live build
DOES have a launch path** — `toolkit/harness/livesession.py`, and the procedure is
§"Capturing a live session" below. This line read "no launch path yet, on purpose" until
2026-08-17, which was true when it was written on 2026-08-06 and false from the next day:
the driver landed 2026-08-07 and six live captures are in the vault. It sat ten days
contradicting the section it shares a document with — the exact staleness failure the top
of `CLAUDE.md` is about, found by an operator following this file to set up a live run.

Which live build to use is a question about the ACCOUNT's client, not about the vault:
`run-live/2026-07-29_221c13772c7a` is **build 38797**, and as of 2026-08-21
**`run-live/2026-08-20_21511009c460` is build 38849 and is the one to use**
(`buildid.py --exe <path>`, which since 2026-08-17 reads the binary you hand it rather
than the pin). **`run-live/2026-08-13_64fae3b1369b` no longer holds what its name says:**
it was build 38833 until the updater rewrote it in place mid-run, and it now holds an
**unpatched 38849** — right directory, right classification, no key-tap. Read the build
and the patches, never the directory name. The updater is LIVE on
both by design, so a build older than what ArenaNet currently serves will update itself —
and the key-tap cave is patched at a build-specific address, so an exe replaced by the
updater loses its tap. `livesession.py` refuses an untapped build at preflight and again
when it reads the slot, so this fails loudly rather than producing unrecoverable
ciphertext; the fix is `make_custom_client.py --no-dh-patch --key-tap` then
`make_run_dir.py --live` against the current build.

**IT UPDATED MID-RUN, AND `updatecheck.py` CANNOT SEE IT. Observed 2026-08-21**,
capture `20260821T145437`, and the recovery is NOT the one-time setup above.
ArenaNet published **38849** while a live run was in progress. The updater is LIVE
on `run-live/` by design, so it rewrote **that copy's `Gw.exe` in place** — all four
patches gone (`mutex=intact name=stock`), the key-tap cave with them, **0 keys
tapped**, and 336 KiB of real ciphertext that nothing can decrypt. The driver's
before/after binary hash is what named it; it is why that check exists.

Three things make this different from the documented update path, and each one
blocks the obvious move:

1. **`C:\gw` was NOT touched** — it is the owner's install and nothing launched it,
   so it stays at the old build. `updatecheck.py --before/--after` reads `C:\gw`
   and has no target override, so it compares a build that did not move and
   truthfully reports **nothing changed**. The update is real and the tool is blind
   to it. Diagnose against the binary instead:
   `buildid.py --exe <run-live exe>`, `dump_dh_params.py <exe>`, and a hit count for
   `keytap_patch.TAP_SIG` (**1** means the cave still has its anchor).
2. **Rebuild FROM THE UPDATED BINARY, not from `C:\gw`.** `C:\gw` is now the *older*
   build, so patching it produces a client that auto-updates on the next live run and
   loses the cave again — today's failure, repeated. The updater leaves a clean stock
   exe of the current build, which is exactly the right `--input`. There is no full
   `vault/client/<tag>/` snapshot of a build acquired this way; do not fabricate a
   partial one, and do not let `pinned.py` acquire a row implying otherwise.
3. **Register the rotated stock parameters FIRST or the patcher refuses.**
   `make_custom_client.py` cross-checks its own output with `dhbuild.classify` and
   requires `stock` for a `--no-dh-patch` build. A rotated prime matches nothing in
   `vault/keys/`, classifies `unknown`, and the build **fails verification** — which
   is the guard working, not a bug. Write `vault/keys/dh_params_<tag>.txt` with
   `root`/`generator`/`prime`/`server_public` (read them with `dhbuild.read_params`),
   note in its header that the source was the updater rather than a snapshot, then
   build. Vault only — never commit.

The sequence that recovered it, in full:

```bash
python toolkit/clientpatch/make_custom_client.py --input <updated run-live exe> --no-dh-patch --key-tap --no-updater-patch
```

```bash
python toolkit/clientpatch/make_run_dir.py --live --patched <the Gw.live.<tag>.exe it wrote>
```

**Pass `--patched` explicitly.** Once a build is added there are three stock exes in
`client-patched-live/` and selection among equals is the `sorted(...)[-1]` defect this
repo has already been bitten by three times in three files. Then `dhbuild.py` must
show the new directory `stock` / `updater=LIVE` / key-tapped, and the **old** run-live
directory is now a trap worth knowing about: it holds an *unpatched* current-build exe
under a directory named for the *previous* build's DH tag, so it classifies `stock` and
sits in the right folder while having no cave. `livesession.py` refuses it at preflight
for exactly that (`key_tapped` false) — which is the only reason a wrong pick is loud
instead of another zero-key run.

**AND THE BUILD GATE'S "SERVICE" IS A PROXY THAT ONLY YOU CAN REFRESH. Observed
2026-08-21, immediately after the above.** `check_build_matches_service` compares the
launch exe against `service_build()`, whose docstring calls `C:\gw` *"the owner's
auto-updating install"*. **It does not auto-update — it updates when it is LAUNCHED**,
and the standing rule is that we never launch it. So the moment ArenaNet ships a build,
the proxy is stale until the owner personally opens their own client, and the gate is
comparing against a build the service stopped serving.

What that looked like: a correct, freshly-built **38849** client was refused with
*"the launch client is build 38849; the live service is serving 38833"* — the exact
reverse of the truth. The service was serving 38849; `C:\gw` was the stale one.

**FOLLOWING THE REFUSAL'S OWN ADVICE REPRODUCES THE FAILURE IT EXISTS TO PREVENT**,
and this is the part worth reading twice. It says *"NO staged live build is 38833.
Rebuild."* Rebuilding against a stale `C:\gw` yields a **38833** client; its updater is
LIVE by design; it self-updates to 38849 on login; the build-specific key-tap cave is
lost in the copy that runs; **0 keys tapped**. That is precisely the failure documented
in the section above, arrived at by obeying the guard.

**The fix is to refresh the proxy, and it is the owner's action, not a tool's.** Launch
the owner's own install once and let it patch. Adding `-image` fetches the full content
image while you are there, which is worth doing: `make_run_dir.py` sources `Gw.dat` from
`C:\gw`, so a current install also means the live run starts with complete content
instead of streaming during the session. Then re-run `make_run_dir.py --live --patched
<exe>` so the staged directory picks the refreshed archive up — it re-copies on a size
change and skips otherwise.

**Check it is really the same build before trusting the agreement**, because "both read
38849" is weaker than it looks — a build number is 5 digits and the exe is 10 MB. Compare
the **sha256 of `C:\gw\Gw.exe` against the source the patched build was made from**; on
2026-08-21 they were byte-identical (`21511009c460a2a9...`), which is what actually
established that the staged client is the binary the service serves. The `-image` content
files land in `Gw.dat` and do not touch the exe, so they cannot change that answer.

**A cheap tightening nobody has built yet:** if any staged `run-live/` binary reads a
HIGHER build than `C:\gw`, the install is provably stale — the only way a `run-live` copy
reaches a higher build is the service having served it. That inference needs no network
and would turn today's misleading refusal into "your install is behind; launch it once".
Unbuilt as of 2026-08-21, and deliberately not written minutes before a live run.

**4. Cage the patched client** (elevated PowerShell, one time per patched exe):

```bash
powershell -ExecutionPolicy Bypass -File C:\gd\Rurik\toolkit\clientpatch\isolate_client.ps1
```

Blocks all outbound traffic from the patched exe except loopback. `C:\gw` is
untouched, so the real client still reaches the live service normally — capture
sessions will need that. Undo with `-Remove`.

---

## What a good run looks like

Terminal 2, in order:

```
[c1] auth version: build=38797 h0008=1 h000C=4
[c1] key exchange OK — ARC4 key …
[c1] c2s 0x8001 SEND_COMPUTER_INFO
[c1] c2s 0x8002 SEND_COMPUTER_HASH
[c1] s2c SESSION_INFO (0x0001, 10B)
[c1] c2s 0x8038 PORTAL_ACCOUNT_LOGIN
[c1] login OK — <your account name>
[c1] s2c CHARACTER_INFO / ACCOUNT_SETTINGS / FRIEND_STREAM_END / ACCOUNT_INFO
[c1] s2c REQUEST_RESPONSE(OK)
```

Then heartbeats with a rising tick counter, which is a healthy idle client.

---

## When it goes wrong

| Symptom | Meaning | Do this |
|---|---|---|
| Stuck on `Connecting to ArenaNet`, no sockets, servers see nothing | The cage is blocking the pre-login patcher's update check — which means this build has no updater kill switch | `python toolkit/clientpatch/dhbuild.py`. If `updater=LIVE`, rebuild with `make_custom_client.py` rather than opening the cage. See below |
| `REFUSING to launch … carries OUR Diffie-Hellman parameters` | A DH-patched client was aimed at a non-loopback host | Correct — that is the account-ending case. Use the `--no-dh-patch` build under `vault/run-live` |
| `REFUSING to launch … carries ArenaNet's Diffie-Hellman parameters, not ours` | The live-capture build was aimed at loopback | Use the copy under `vault/run`; the live build cannot key against our server |
| `REFUSING to launch … no Gw.dat, so staging did not finish` | `make_run_dir.py` could not copy the 4 GB source | Close every `Gw.exe` (a running one holds it open exclusively) and re-run `make_run_dir.py` |
| `REFUSING to launch from …Gw.dat` naming an open-time rule | The ARCHIVE gate, not the cage — `datcheck.assert_archive_safe`, wired beside `cage.assert_launch_safe` at all four launch sites 2026-08-20. The launch is the irreversible step: a bad header tail-jumps into ArchiveCreate (a fresh empty archive over 4.2 GB, nothing logged), and repair DISCARDS any chain whose payload CRC mismatches | The refusal names the rule and the remedy; stopping here is the point. `python toolkit/mapdata/datcheck.py --dat … --assert-safe` reproduces it standalone |
| Archive gate says `PermissionError … A client already running holds this archive open` | A lock, not damage | Close every `Gw.exe` and re-run. Only if nothing is running does "unreadable" mean the file itself |
| Archive gate says `MFT self-crc is stored X, computed Y` | A grow-without-resync (`datwrite.py:755-781`): `--preflight` still answers 10/10 clear, and the client's own LoadMft would still reject it | Revert the write from its journal, or restore the overlay/retail copy — do not launch |
| Archive gate says `row(s) whose payload does not match its stored CRC` | Launching would let repair delete those whole `nextStream` chains | `datcheck --crc-sweep` names the rows; restore via the write's journal, `overlay.py --retail`, or `datdelta.py --apply` |
| `REFUSING to launch: content/maps.toml disagrees with the archives this run would use` naming a map you did not touch, **after a client run that loaded it** | Not damage and not your change: the client **writes to its own `Gw.dat`** as it patches content (`make_run_dir.py`'s header — a run directory is "a point-in-time working copy, not a reference"), so a map it loaded can end up re-pointed at an appended row that no longer matches the frozen `vault/dat_study` copy the server reads. Seen 2026-08-23 on Ascalon City `0x1B97D` after two loopback runs. **The gate is loopback-only by design** (`drive_client.assert_safe`), so a LIVE capture is not affected | `python toolkit/contentids.py` names every diverging row. If the run does not load that map, pin the one it does — `--game-args "--map N"` narrows the pre-flight through `session.served_maps`, and the refusal still prints `[FATAL, not served]` rather than hiding it. **Pin a map with a REAL SPAWN, and check before you pin**: most `content/maps.toml` rows carry `spawn_x/y = 0.0` under a "No spawn point known" note, and a run pinned to one of those puts the character at the world ORIGIN, off the walkable mesh, where it cannot move at all — seen 2026-08-24 with `--map 90` (Lornar's Pass), where the client reported position `(0.0, 0.0)` and every movement grant fired against nothing. **`--map 280`, the Isle of the Nameless, is the one to reach for**: archives agree, `explorable = true`, training dummies, and its spawn is retail's own arrival position (byte-identical on six live loads, walkability-checked). If the run DOES load the diverging map, the archives must be reconciled first (re-stage from `C:\gw` with `make_run_dir.py`, or refresh `dat_study`) — that is an owner decision, not a launch-time one. **MEASURED 2026-08-27, and for map 146/148 TODAY the cause is GENERATION SKEW, not the mechanism this row describes.** The run dirs' copy is byte-identical to `vault/dat_study_38833` -- row 177262, 1,300,044 B, crc `0x33F1A289` -- against `dat_study`'s 38797-era row 7982 / 1,300,036 B / `0xA0AE500A`. **All three current run dirs land on the SAME row index**, which independent client-side appends could not produce; they were re-staged from a 38833 source while `dat_study`, the archive the SERVER reads, is still a 38797 snapshot. So CHECK THE GENERATION BEFORE SUSPECTING DAMAGE: this is a re-stage away from fixed, and `datcheck`'s repair paths are the wrong tool for it. (The client-writes-its-own-`Gw.dat` mechanism above is real and is still the right first guess for a map the run actually loaded; it is simply not what these bytes are.) Note the naming trap: `run/2026-07-29_221c13772c7a` carries the **38833** map -- a run dir is named for its EXE build and its archive has moved on. The rest of the census stands:  ALL THREE current run dirs (`2026-07-29_221c13772c7a`, `2026-08-13_64fae3b1369b`, `2026-08-20_21511009c460`) carry the same modified `0x1B97D` — 1,300,044 B crc `0x33F1A289` against `dat_study`'s 1,300,036 B crc `0xA0AE500A` — while the older dirs are the mirror image, agreeing on 146/148 and differing on map 143 instead (`-c2` 4,352 B, `-probe` 1,168 B, `reskin-roster` 6,012 B against 9,284 B). So there is NO run directory that agrees with `dat_study` on every content map row, and pinning a map is not always available.** A third route the rest of this row does not mention, and the one used for the MAPID confirmation: point the SERVER at the archive the client actually draws — `RURIK_DAT="<run dir>/Gw.dat" python toolkit/harness/session.py`. `contentids` then reports 12 of 12 agreeing. It reconciles nothing and writes nothing; it removes the divergence by making both sides read the same bytes, which is precisely the hazard the gate names ("the server would path against geometry the client is not drawing"). ~~Whether `dat_study` should be re-synced instead remains the owner decision this row already describes.~~ **RESOLVED 2026-08-27 — the owner ruled RESYNC, and it is done.** `vault/dat_study/Gw.dat` is now the **38833** generation and `contentids` reports **12 of 12 agreeing with no `RURIK_DAT`**, so the workaround above is no longer needed for the current run dirs. **Source was `vault/client/2026-08-13_64fae3b1369b`, the pristine snapshot — NOT `vault/dat_study_38833`**, which is a preserved regression fixture whose live file-id table destroyed the `Mft` magic and left a 2,892,800 B orphaned tail that `datmove.plan_move` allocates into (`studies/archivewrite/FINDINGS.md` §1.5); promoting it would have put that trap under the server's own archive. **Nothing was deleted**: the outgoing 38797 archive is `vault/dat_study_38797/Gw.dat` and the fixture is untouched, so every 38797-pinned measurement and the crossbuild work keep their reference — point `RURIK_DAT` at it to reproduce an old number. Verified byte-for-byte, not just by size: MFT sha256 `4ce9ef10dce12583`, self-crc `0xA1F24741`, 177,738 payload CRCs recomputed, 10 of 10 open-time rules |
| A dry-run or session dies at `the client keyed the auth channel … no handshake within 150s` | The client never LAUNCHED — this checkpoint is downstream of the launch, so it reports the timeout rather than the cause | Read `vault/dryrun/dryrun_session.log` (or the session's own output). A `REFUSING to launch` block there is the real answer; the row above is one way it happens |
| `Unexpected token '-authsrv'` | PowerShell parsed the quoted path as a value | Add the leading `&`. Nothing launched; the flags are fine |
| `Could not bind … Another AuthSrv is almost certainly still running` | Working as intended | `netstat -ano \| findstr :6112`, stop the old one. Note a healthy stack shows TWO 6112 listeners — auth on `127.0.0.1`, game on `127.0.0.3`; the stale one is at the host you are trying to bind. This replaced a silent-shadowing bug that cost two sessions |
| `Code=058`, nothing in terminal 2 | Client never reached us | Both flags present? Launched the **run-dir** copy, not `C:\gw\Gw.exe`? |
| `expected 0x4200, got …` | Key exchange never started | Almost always an unpatched client |
| `login REJECTED — no session` | Portal and AuthSrv disagree | Restart the webgate so it re-issues, or use `--allow-any-session` to prove the rest of the path works |
| Client hangs after login | A reply field is wrong | `ACCOUNT_INFO` has three fields marked low-confidence at the call site — start there. See below |
| Roster empty but login succeeded | Campaign gate | Try the all-campaigns bitmask `b'\x3f' + b'\x00'*7` in `ACCOUNT_INFO` |
| `undecodable` in terminal 2 | Unknown opcode, framing stopped | Correct behaviour — it refuses to guess. The printed leading bytes are the next thing to identify |
| Pressing **M** (world map) kills the client on `Assertion: worldMapDims.x == mapDims.x * DXT_BLOCK_SIZE` (`GmMapView.cpp:1731`) within ~2 s, and the crash dialog then **takes focus, so every later scripted key goes to the dialog** — the harness still logs each press `sent` and can score the run PASS | **A known server gap, not archive state and not damage**: the world map sizes its texture from `charContext+0x5B4`, which only the fog-of-war init pair `0x008B`+`0x008A` writes — with no init, `mapDims` is 0 and the compare dies. Proven by a matched pair (`studies/minimap/FINDINGS.md` §6f.2: same archive, pair sent → the map opens); reproduced on 38797 2026-08-24, `vault/captures/harness/20260824T065948/crash-dialog.txt`. **FIXED at the server 2026-08-24 for continent-1 maps** (148/146/143/165/166): `authsrv.py` sends the pair at map load with a synthetic all-fogged stream (`fogrle.py`, FINDINGS §6i), so a stock run's M press is safe there | If this fired after 2026-08-24, the load log says why: `FOG INIT SKIPPED` names a continent with **no observed dims** (0/2/3/4/5 — Ashcoil's slot 167 included; one retail capture on that continent settles its `content/fog.toml` row), and `FOG INIT OFF` means the run passed `--no-fog-init` (the pre-fix baseline, needed by experiments that want `0x008C` inert). In either of those worlds do not script `key:m`, and never ahead of arms you still need — one M press voided a whole probe run (`studies/playercomposite/FINDINGS.md` §9.22) |
| Anything at all after an ArenaNet update | Parameters rotated | `python toolkit/updatecheck.py --after <baseline>` first — it names what moved and what still resolves — then redo the one-time setup in full |
| `the launch client is build N; the live service is serving M`, where **M is older than N** | The gate's "service" is `C:\gw`, which updates only when LAUNCHED -- so it is stale, not the service. Do **not** follow the refusal's advice to rebuild against it: that yields a client older than the service, which self-updates mid-run and loses the key-tap cave | Launch the owner's own install once (add `-image` to fetch full content), then re-run `make_run_dir.py --live --patched <exe>`. Confirm by sha256 that `C:\gw\Gw.exe` matches the source the patched build was made from |
| A live run ends `0 distinct session key(s) tapped` **and** `THE CLIENT BINARY CHANGED DURING THIS RUN` | ArenaNet published a build mid-session; the LIVE updater rewrote `run-live/`'s exe and the key-tap cave went with it | **Not** the row above — `updatecheck.py` reads `C:\gw`, which the update did not touch, and will report nothing moved. See §"IT UPDATED MID-RUN" above: rebuild from the *updated* binary, and register the rotated stock params before the patcher will accept it |

**Never point a patched client at the real service.** It carries our DH values, so
it cannot key with ArenaNet's — and the attempt is exactly the kind of malformed
traffic worth not sending.

---

## The patcher stall, and why it read as innocent

Diagnosed 2026-08-04. Worth writing down because the evidence pointed the wrong
way for half an hour.

The client hung on *Connecting to ArenaNet* — which is the **patcher**, not the
login: that string sits in the same localized block as `Downloading...` and
`Downloading %u.%uMB (%uKB/sec)`. The cause was the cage's outbound block denying
the patcher's update check.

What made it hard: **a Windows Firewall outbound block fails `connect()`
immediately rather than black-holing it.** The socket never reaches `SYN_SENT`,
so it never appears in a sample. Twenty-four samples over twenty seconds found no
sockets at all, which reads as *the process is not using the network* — the exact
opposite of the truth. The tell was two threads parked in `ExecutionDelay`, i.e.
`Sleep()`: try, denied instantly, sleep, retry, forever.

Two other traps in the same hour:

- `Get-Process().Modules` against `Gw.exe` returns only `ntdll` and the wow64
  shims. That is not a half-initialised process — it is a 64-bit query against a
  32-bit process, which cannot see the 32-bit module list. It means nothing.
- `Gw.tmp` appearing at 0 bytes next to the exe looks like an interrupted
  download. It is a normal startup scratch file; the live install has one too.

What actually settled it was an A/B: the **unpatched, uncaged** client at
`C:\gw\Gw.exe` with the same flags walked straight past the patcher to the login
screen, then died at key exchange exactly as the negative control predicts
(`AUTH_CMSG has no opcode 26763` — our ARC4 keystream against its ArenaNet-keyed
one). Same machine, same flags, one variable.

The client's own log is the fastest way in. `-log` is live and writes `Gw.log`
beside the exe, but it **buffers and only flushes on exit** — a stuck client shows
0 bytes. Close it, then read.

---

## Capturing a live session (R0b), and its two elevated steps

The live-capture driver records a real session against ArenaNet on the **secondary
account** and turns its wire bytes into a decrypted, `origin: live`, byte-replayable
capture. Every part is built and proven offline; two steps need an elevated shell and are
deliberately not automated.

**How it works.** The stock-DH live build (`vault/run-live/`) must carry a **key-tap** cave
— check with `python toolkit/clientpatch/dhbuild.py`, and if `key_tapped` is false rebuild
with `make_custom_client.py --no-dh-patch --key-tap` then `make_run_dir.py --live`
(`Gw.dat` is not re-copied). `livesession.py` refuses an untapped build, because without
the cave there is no key and the ciphertext is unrecoverable. The cave copies `master_secret`
to a data slot as the handshake runs; `keytap.py` reads it back. The ciphertext is captured
**off the wire** with WinDivert (`wirecapture.py`, SNIFF mode — it observes, never alters).
`livesession.py` assembles the two: it splits the plaintext DH handshake off each direction
and decrypts the rest, and `replay.py`/`scrub_captures.py` verify and redact. The launch is
bound by `cage.assert_launch_safe` (stock→live, uncaged), the account by
`accounts.for_automation` (the primary is refused), and the run is gated behind `--confirm`.

**Elevated step 1 — load WinDivert, once.** The binaries live at
`vault/tools/windivert/` (not in git; see its `PROVENANCE.txt` — WinDivert 2.2.2, official
`basil00` release, kernel driver signed and owner-accepted). The **first** `WinDivertOpen`
installs and starts a kernel service, which needs admin. From an **elevated** shell:

```bash
python toolkit/harness/wirecapture.py --pid <client> --server 127.0.0.1:6112 --seconds 20 --out C:\gd\Rurik\vault\captures\live\dryrun.jsonl
```

**Do the loopback dry-run before going live.** The whole pipeline — key-tap → off-wire
capture → keytap → assemble → decrypt — runs against our own server first, where every byte
has an oracle. It is one elevated command and it cleans up after itself, including
restoring the loopback client to its untapped default:

```bash
python toolkit/harness/dryrun_keycapture.py
```

**Step 2a — write the marks plan FIRST, before anything launches.** Skipping it is not an error
and the driver will not stop you, but the capture comes out *unlabelled* — which is what every
live capture before 2026-08-13 already is. The plan is one `kind<TAB>text` line per thing you
intend to do. It is a **pre-registration**: it states what you expect *before* you do it, and
after the run it is what the marks mean.

```
open	merchant Sanura, first open
buy	one salvage kit
open	Sanura again, second open
```

Check it parses, then leave the file untouched for the rest of the session:

```bash
python toolkit/harness/marks.py --check-plan C:\gd\Rurik\vault\plans\kryta_merchant.txt
```

**Elevated step 2 — the live run itself.** Only after the dry-run is green. Owner-driven,
one client, human cadence, human hours, never in a competitive context (`PLAN.md` §6.1 —
the traffic *pattern* is what closes accounts, and no gate substitutes for that):

```bash
python toolkit/harness/livesession.py --account capture --exe C:\gd\Rurik\vault\run-live\<build>\Gw.exe --confirm --mode base --plan C:\gd\Rurik\vault\plans\kryta_merchant.txt
```

**`--plan` is OPTIONAL — the run is worth taking without it — but pass it.** The driver hashes
the plan **before the client launches**, prints the sha256, and writes it into `manifest.json`.
A plan hashed at the *end* would certify whatever it said afterwards, which is worse than no
seal because it looks like evidence. Without `--plan` the run prints a loud
`*** THIS RUN HAS NO PRE-REGISTERED PLAN ***` block and records `"plan_sealed": false` rather
than omitting the key — and it deliberately offers **no** `marks.py` command, because a plan
written after the client launched is a label, not a prediction.

**Step 2b — the second shell, started before you log in.** The driver prints the exact command
with the resolved capture directory and the client pid. **Copy it; do not retype it** — a
different file with the same name seals nothing and `marks.py` cannot tell, since the mismatch
is only reported after the run. Then, while you play:

- **F9** advance — the next plan step
- **F10** repeat — you did that one again
- **F11** note — stamps the instant with **no text**; you annotate it afterwards by ordinal in a
  separate notes file, which is what keeps anything you type out of the capture

The keys are registered globally and **swallowed**, so they never reach Guild Wars — which is
why they are F9–F11, and why `marks.py` refuses rather than falling back to polling if
something else already holds them. Free them before the run.

Its output is `plan_marks.jsonl`, **not** `marks.jsonl`. Those are two different channels and
they stay separate (owner's ruling, 2026-08-13): `marks.jsonl` is the harness narrating itself,
`plan_marks.jsonl` is a human acting against a sealed plan. Afterwards `manifest.json`'s
`plan_seals` field reports **AGREE / DISAGREE / UNCHECKED** — the driver's pre-launch hash
against the marker's own independent read, which is the only thing that can catch a plan edited
between the launch and the first mark.

**`--mode base|reforged` is REQUIRED and has no default — check the account before you
type it.** Reforged Mode changes enemy health and armour by roughly 20%, and **nothing in
the recorded stream says which mode produced it**, so it cannot be recovered afterwards:
every health number from an unstamped capture is base or base × 0.8 forever, and ~20% is
exactly the size that reads as a plausible base value rather than an obvious error. The
driver refuses before it launches anything, because this is the one question that cannot
be asked after the fact. **State what the account is actually set to, not what you meant
to set it to** — a wrong answer is worse than the refusal, since it stamps a number that
then looks trustworthy. The value lands in `manifest.json` as `game_mode`, labelled
`game_mode_source: operator-declared`: it is the only field there that is not derived from
an artifact, and nothing checks it, because Reforged Mode leaves no mark we have measured.
The three monster health readings already in the vault predate the flag and are
`mode = "unrecorded"` — kept, never promoted.

**Do not pass `--host`, and it is refused if you do.** This line used to carry
`--host <auth ip>` and that was wrong in a way that looked like success. A live login is
three stages on three endpoints, and Stage C's game-server address arrives *inside* the
ARC4-encrypted `AUTH_SMSG_GAME_SERVER_INFO` — so it cannot be known when the packet filter
opens and cannot be added later. Pinning the sniff to the auth IP records the auth channel
only, prints `1/1 connection(s) decrypted`, exits 0, and spends the one authorized session
on the only channel loopback already reproduces. The sniff filters by **port on any host**.

**What the driver does and does not do.** It starts the sniff *before* the launch (the DH
handshake is the first thing on the wire and it is the plaintext half), launches with no
`-portal`/`-authsrv` so the client uses its own compiled-in ArenaNet endpoints, polls the
tap for a **keyring** — each channel overwrites the one slot, so one read loses a channel —
holds to `--minutes` (default 10 — a **ceiling, not a duration**: Ctrl-C ends the session
at any point and still assembles and scrubs in full), then closes the client with `WM_CLOSE` so `Gw.log`
survives, and assembles per connection. **It sends no keystrokes and no clicks.** You log
in and play; the driver only instruments. That is deliberate: the loopback harness's
scripted three-Enters-and-a-Play-click is precisely the traffic pattern §6.1 warns about.

**MARK WHAT YOU ARE ABOUT TO DO, from any shell.** The driver writes `marks.jsonl`
and watches for a `MARK` file beside `STOP`; its contents become the label:

```bash
echo approach > C:\gd\Rurik\vault\captures\live\<stamp>\MARK
```

`session_start` and `session_end` are taken automatically, so even an unmarked run
is bracketed.

**OR LET THE SCRIPT DO THE MARKING.** `behaviourrun.py` carries the campaign's step list
and walks it for you in a second shell, writing each `MARK` as it goes. It prints a
sentence, you do it, the timer runs out. It sends nothing to the game:

```bash
python toolkit/authsrv/behaviourrun.py --narrate C:\gd\Rurik\vault\captures\live\<stamp>
```

Read it first with `--script`, which prints each step with the reason it exists. And run
`--preflight` once before the first session: it checks the tick clock against the wire
clock on the captures already in the vault, and a red there means the mapping every timed
claim in this repo rests on is broken and a live session is not the thing to spend next. Use the same file mechanism as `STOP` and for the same reason: you
are looking at the game window, so anything needing console focus is advice that
fails exactly when it is needed.

**Why it matters, and it is not bookkeeping.** Every captured segment is stamped
`perf_counter() - t0` with `t0` taken *inside the sniffer subprocess*, and
CPython's contract says that clock's reference point is undefined — only
differences within one call site mean anything. So a capture's timestamps used to
be offsets from an origin **no other process could name**, and the only other
clock in the artifact was `manifest.json`'s stamp, taken in the parent *before*
the sniffer was spawned. A narrated session could be aligned to its narration only
after the fact and only to within seconds, which is exactly the gap-inference
failure `labelrun.py` exists to end. Captures now record `t0_wall` so every `t`
converts to absolute UTC, and each mark carries **three** numbers — wall, the
parent's perf, and the capture's own last segment `t` — so the two channels can
be required to agree instead of trusted. `wirecapture.mark_skew()` reports the
per-mark skew and names any disagreement; a capture written before 2026-08-11 has
no epoch and it **refuses to place it on a clock** rather than substituting the
manifest stamp. See `studies/monsterai/FINDINGS.md` §7.1.

**Output**, under `vault/captures/live/<stamp>/`: `wire.jsonl` (the raw off-wire capture,
kept even if nothing decrypts), `keyring.jsonl` (**every tapped key, written and flushed
the moment it is read** — the first run held them in memory and lost six of seven, which
made six channels of captured ArenaNet ciphertext permanently undecryptable), one
`<channel>-<connection>.jsonl` per decrypted channel, `marks.jsonl` (the narration binding — empty is a red flag, not a neutral result: it means the driver never even took its two automatic anchors), and `manifest.json`. The scrubbed
copy goes to `vault/captures-scrubbed/live-<stamp>/`, outside the capture tree so censuses
and the tree-wide scrub do not walk it as if it were more evidence.

**A capture can be decoded again without a client, a network or an account** — that is
what the keyring is for, and it is how a framing fix gets applied to bytes already on disk:

```bash
python toolkit/harness/livesession.py --assemble C:\gd\Rurik\vault\captures\live\<stamp>
``` **`scrubbed/` is not shareable.** The scrub matches JSON
keys and cannot see inside a `plain` hex blob, and the auth channel's first client message
carries the account email as UTF-16 inside exactly such a blob. The scrub says so on the
way out and `SCRUB-MANIFEST.json` names every file affected — this applies to the existing
`captures-scrubbed/` tree too (MEASURED: 401 of 517 vaulted captures carry one).

## Where the pieces live

| Path | What it is |
|---|---|
| `toolkit/harness/livesession.py` | The live-capture driver: launch gate + account + key-tap + off-wire capture + decrypt + `origin: live` + scrub, behind `--confirm` |
| `toolkit/harness/wirecapture.py` | Off-wire ciphertext capture (WinDivert SNIFF); the DH handshake is plaintext on the wire, the rest is ciphertext |
| `toolkit/harness/keytap.py` | Reads the session key out of the running client (`ReadProcessMemory`, ASLR-correct) — what the code cave stashed |
| `vault/tools/windivert/` | WinDivert 2.2.2 (gitignored, third-party). First `WinDivertOpen` needs admin |
| `toolkit/portal/webgate.py` | Stage A, the portal (HTTP, 6601) |
| `toolkit/authsrv/authsrv.py` | Stage B, auth + the encrypted channel (6112) |
| `toolkit/portal/sessionstore.py` | Shared state between the two, plus the UUID wire encoding |
| `toolkit/schema/` | The 777-message catalog and the codec |
| `schema/messages.json` | The wire schema itself (tracked in git) |
| `toolkit/clientscan/` | Read-only client analysis |
| `toolkit/clientpatch/` | Patching, run-dir assembly, the firewall cage |
| `toolkit/clientpatch/dhbuild.py` | What a `Gw.exe` **is**, read from its bytes: whose DH parameters, which patches |
| `toolkit/clientpatch/cage.py` | The launch gate — binds a binary's DH parameters to the host it may be aimed at |
| `toolkit/clientpatch/launch_caged.ps1` | **Legacy.** Elevated launcher that opens the cage for the patcher. Refuses any build with the updater kill switch, i.e. all of them |
| `vault/` | Gitignored. Client snapshots, keys, captures, prior-art mirrors |
| `vault/dat_study/Gw.dat` | A third copy of the archive, for reading map data. See below |
| `studies/handshake/PLAN.md` | How R1 was actually solved, wire detail included |
| `studies/movement/FINDINGS.md` | What we know about movement, and from whom |
| `studies/mapdata/FORMAT.md` | Reading map geometry out of the archive |
| `PLAN.md` | Strategy, the ladder, ranked angles of attack |

---

## Backing up the vault, and the one thing that blocks going off-disk

The vault is the only part of this project that cannot be rebuilt. Code regenerates
from git; two pinned ArenaNet builds do not, and ArenaNet's own updater has already
replaced one in place mid-session. `vault/client/` alone is 8 GB of that, and its
directory names are the sha256 prefixes of the binaries inside, so a copy verifies
itself.

**The mirror.** Same-disk, so it covers the failure with history here — an install or
a script overwriting files — but not the disk dying:

```bash
robocopy C:\gd\Rurik\vault C:\gd\Rurik-Backups\vault /MIR /R:1 /W:1 /MT:8 /NP /NFL /NDL
```

Robocopy exit codes 0–7 all mean success; 1 is "files were copied". Check `FAILED : 0`
in the summary rather than the exit code. Last full run: 20,855 files, 20.897 GB,
about three minutes, both client `Gw.exe` hashes verified equal afterwards.

**Off-disk is the copy that matters, and it needs the scrub first.** The client sends
the owner's real ArenaNet credential to our own webgate on every login and we record
it, so `vault/captures/portal/` carries the account email, the password as base64, and
every issued session token. Nothing has ever been in git — `vault/` was gitignored in
the first commit — but that set cannot leave the machine as it stands. It is a filter,
not a blocker:

```bash
python toolkit/scrub_captures.py --force
```

Writes `vault/captures-scrubbed/`, mirroring the whole capture tree, and never touches
the originals — they stay as recorded, because an original capture is evidence about the
protocol and a scrubbed one is only evidence about a session.

**This used to cover `captures/portal/` alone, and the recipe below used to say "take
everything except `run/` and `dat_study/`."** Measured 2026-08-06, that shipped **206
`email` records, 113 `account_uuid`, 113 `char_uuid` and 341 ARC4 keys and DH seeds**
sitting in `authsrv/`, `gamesrv/` and `selftest/` — none of which the scrubber looked at.
The recipe was the exposure, not the vault.

Placeholders are assigned sequentially rather than hashed (the password is short enough that a
hash would be brute-forceable), are the same length as what they replace so
`Content-Length` and the base64 width stay honest, and are one-to-one so the same value
lands on the same placeholder everywhere — correlation survives, identity does not.

`toolkit/test_scrub.py` harvests every secret out of the originals with **its own** field
list and asserts not one appears in the output. That check has now caught three fields
nobody had listed: the reply body's `<Session>`/`<Token>`/`<UserId>`, the entire
`authsrv/` directory, and `who` — a `login_ok` log line with an account UUID and a session
token embedded in prose, which whole-value substitution could never have fixed. Re-run it
after touching any list.

**`.raw` files are NOT scrubbed and NOT copied — 342 of them.** They are the undecoded
byte stream, nothing in the toolkit parses them, and the portal stage is plaintext HTTP,
so they may hold the credential directly. Anything that leaves this machine must exclude
them until someone does that work.

For an off-disk copy: **`client/`, `mirrors/`, `keys/`, `research/`, and
`captures-scrubbed/`** — roughly 10.5 GB, a USB stick. Not `captures/` (unscrubbed, and
carries the `.raw` set), not `run/` or `dat_study/` (11.9 GB, both regenerate from
`client/` plus the patcher and `Gw.dat`).

## Playing a tape

A tape replays one recorded game connection's server plaintext into a fresh loopback
session at its recorded timing. No live client, no ArenaNet, no new capture. What it
proves and what it cannot is [studies/tape/FINDINGS.md](studies/tape/FINDINGS.md); this
is the procedure.

**1. Pick the tape by decoding it, never by position in the session.** A capture holds
several game connections and the interesting one is rarely the obvious one — on
2026-08-10 the Lakeside tape with the combat in it was the operator's *second* visit, not
the one that follows Ascalon.

```bash
python toolkit/authsrv/tape.py
```

That lists every playable connection with its event count, byte count and cadence. To
name the maps, read each connection's own c2s `VERSION` body — `<5I>` at offset 4 is
build, unk1, world_id, **map_id**, player_id — and resolve `map_id` through
`vault/research/areainfo_38797.json`.

**2. Pre-flight the archive.** Get the `map_file_id` out of the tape's `0x0195` and check
both `run/Gw.dat` and `run-live/Gw.dat` resolve it, per "The two run directories drift
apart" below. A missing id is `Map.cpp(1762)` about thirty seconds into the run.

**3. Play it.**

```bash
python toolkit/harness/session.py --keep-open --game-args "--tape C:\gd\Rurik\vault\captures\live\20260807T143055 --tape-connection 10.0.0.210:64103->54.198.7.73:80"
```

`--map` is a **no-op under a tape** — `MAP_OVERRIDE` sets state that the tape path never
reads, and the client will render whatever the tape's `0x0195` names regardless of what
it asked for. Passing it only makes the log say something misleading.

**4. Watch the gamesrv terminal, not the avatar.** This is the one that costs time if you
get it wrong. The recorded operator stands still whenever they stood still — on the
Lakeside tape, for the **last 146 seconds of a 186-second tape** — and from the seat that
is indistinguishable from the tape having finished. The terminal prints `tape N/1074`
every 200 events and `tape complete: N/N events in Xs` at the end. Nothing before that
line means the tape is over.

**5. Measure it before believing it.** The run is only interpretable if our server stayed
silent, and that has been wrong once: count `sent` records in
`vault/captures/gamesrv/authsrv-*-c1.jsonl` whose `label` does not start with `tape[`. It
must be zero. Anything else and the client was hearing two servers, which is how the
2026-08-10 `AgAgent.cpp(978)` assert got attributed to the wrong thing for a day.

**What a tape cannot do:** respond. Tape mode never answers c2s, so after the recording
runs out the client can still move (that is client-side) but attacking, casting and
gateways do nothing. That is the instrument, not a bug.

## Chaining the tapes: one recorded session, four maps

A single tape ends where its recording ended — the operator walked into a gateway, the
server sent `0x01A5 GAME_SERVER_TRANSFER`, and the client dialled the next instance.
Chaining repoints that handoff at a loopback server of ours and arms it with the next
tape, so the whole recorded session plays as one run:

```bash
python toolkit/harness/session.py --tape-chain 20260807T143055
```

A bare stamp is enough — the tools find the vault themselves (`toolkit/vaultpath.py`), so
an absolute path, a `vault/captures/live/<stamp>` path and the stamp alone all work. This
line used to read `--tape-chain vault/captures/live/<stamp>` and that **failed from a git
worktree**, which has no `vault/` of its own: the relative path resolved to nothing and
the operator got a `FileNotFoundError` traceback out of `os.listdir`. Same class of bug
`vaultpath.py` exists to prevent, through the one door it did not cover — it was used
everywhere a path was *constructed* and nowhere a path was *accepted*.

That discovers the chain rather than assuming it — each hop's handoff must match the next
connection's own VERSION frame or it is **refused**, never ordered by timestamp — then
starts one gamesrv per hop on `127.0.0.3`, `.4`, `.5`, `.6`, each rewriting to the next.
The last hop is truncated. Expect **4 hops, 184,756 B, ~396 s**: Ascalon City (148) →
Lakeside County (146) → Ashford Abbey (164) → Lakeside County (146).

**Sit still for all of it.** A tape cannot show control (that is `tape.py`'s docstring, not
a bug), and each hop's avatar stops moving well before its tape ends — on the Ascalon tape
that gap is about 146 seconds. The only truthful progress signal is each hop's own
`tape complete: N/N` line, and all four gamesrv instances echo into your terminal for
exactly that reason.

`--tape-chain` turns on `--keep-open` for you and sizes `--hold` from the tapes themselves
(~7 minutes for this capture). **Do not remove it.** The first chain run printed
`RUN VERDICT: PASS (target: map)` and tore the stack down **1.7 seconds into a 396-second
chain**: the verdict answers "did the client reach the map", which under a tape is true
almost immediately and says nothing about the six minutes that are the actual experiment.
The gamesrv then reported `TAPE ENDED at event 59/1209` with a connection reset and listed
the events "in flight" for a client assert that never happened — the reset *was* the
teardown. If you see a tape end early, **check `Gw.log` for an `Assertion` line before
believing it was a crash**: no Assertion means the stack went down, not the client.

One archive pre-flight covers the whole chain: all four tapes declare the same
`map_file_id` 113021.

**What the rewrite costs you.** Before chaining, a tape that reached its handoff failed
*loudly*: the client dialled ArenaNet, the cage refused, and `Code=005` appeared. A
rewritten tape has no such signal — a wrong address is just a connection that never
arrives. `--tape-rewrite-next` therefore refuses any host outside 127/8 and proves the
rewrite offline before the client starts. If a hop goes quiet, read the gamesrv banner:
it names the byte offset and both addresses.

**If a hop loads its map and then sits at "Connecting" forever**, that is the deferred
transfer, not a crash. The client only dials a game-server handoff immediately the *first*
time in a session; after that it stashes the address and waits for the connection it
already holds to end (bit `0x20` at `+0x190`, set by the connect itself — T10). Our server
now hangs up when a tape ends in a handoff, which is what the recorded server does 0.14 s
after every transition. Check the gamesrv for `tape ended in a handoff -- closing`; if it
is there and the client still does not dial, the release needs something else and the run
is worth reporting rather than repeating.

To play one hop alone, skip the chain and arm that connection directly with
`--game-args "--tape DIR --tape-connection CLIENT->SERVER --tape-no-transfer"`. The
Ashford hop is the cheapest thing to test a change against — 14.0 s and 726 messages.

## Burrowing, and the one question only the client can answer

Plague Worms hide by being removed and re-created under the same agent id — 140 times in
186 seconds on one Lakeside tape. The server can now do that (`burrow_tick`), and
`toolkit/authsrv/test_burrow.py` checks the cycle offline against ArenaNet's own bytes.

**One thing is not settled and it gates the interesting half.** ArenaNet sends the NPC
definition (`0x0056`) **once for 140 re-creates**. Ours resends it every time, because
whether a definition survives a removal has never been asked: the `agent_removal` probe
that proved id reuse resent the definition on every step, so its success says nothing
about this. If definitions do *not* survive, dropping the resend crashes the client on
`index < m_count`. So the server resends, and this probe is what would let it stop:

```bash
python toolkit/harness/session.py --enemy --keep-open --game-args '--probe burrow'
```

(`--probe` is a GAMESRV flag and only reaches it through `--game-args` —
`session.py --probe burrow` bare is an argparse error. This line said exactly
that until 2026-08-16. `--enemy` because this probe needs the hostile;
`--keep-open` because a probe's steps land after the spawn verdict.)

**Target the hostile before it starts, and keep watching the target frame.** Steps 3 and
4 are the experiment — the same id and then a fresh id, both with no definition resent.
Both drawing a *correct-looking* collector means a definition is per-instance and
outlives its agents. A body that appears but looks wrong is as informative as no body.

To watch the cycle itself rather than probe it, turn the content flag on:

```bash
python - <<'EOF'
import re, pathlib
p = pathlib.Path("content/world.toml")
p.write_text(p.read_text(encoding="utf-8").replace("burrow = false", "burrow = true"), encoding="utf-8")
EOF
```

The hostile then emerges, stands for `burrow_out_seconds`, sinks and vanishes for
`burrow_hidden_seconds`, forever. **Its two 2.00 s transition windows are measured; the
other two durations are invented** and the content row says so — live, they were not
periods at all. Expect to lose your target on every submerge: `attack_tick` clears
`state["attacking"]` when the target leaves the world, which is correct and means about
eleven re-clicks a minute against a fast worm.

## The labelled input run

Names client-to-server messages by watching a human send them. `schema/messages.json`
carries field layouts for **194 `GAME_CMSG` opcodes and names for none of them**; our
server names 11 by hand and 15 have ever been witnessed from a real client. This is how
that number goes up.

**Pick the script to match the world the tape leaves behind.** This is not a preference;
it decides what can be asked at all:

| script | tape | that world has |
|---|---|---|
| `combat` | Lakeside `:64103` | skillbar `[153, 105, 0×6]`, hostiles, 1 player |
| `town` | Ascalon City `:60935` | 19 NPCs, 40 players, skillbar **all zeros** |

Running `combat` against Ascalon gives eight silent skill steps, which reads as "the
client sends nothing for skills" and is false.

See the script first — it states a prediction per step, and two steps are idle controls:

```bash
python toolkit/authsrv/labelrun.py --script town
```

**ONE command runs the whole thing** — tape, then prompts, in the same terminal. There is
nothing to start separately and nothing to time yourself:

```bash
python toolkit/harness/session.py --keep-open --game-args "--tape C:\gd\Rurik\vault\captures\live\20260807T143055 --tape-connection 10.0.0.210:60935->52.3.40.244:80 --labelrun town"
```

| when | what happens | you |
|---|---|---|
| 0:00 | client launches and logs itself in | nothing |
| ~0:30 | the tape starts; your character walks on its own | **nothing** |
| ~1:20 | `tape complete`, then the labelled-run banner | the steps |
| ~4:50 | `DONE -- N steps recorded` | finished |

Times above are the **town** run: Ascalon's tape is 48.6 s, against Lakeside's 186.2 s.
Swap the `--tape-connection` and drop the script name for the `combat` run, and add two
minutes of waiting.

The first three minutes are the recording driving your client. That is not a malfunction,
and the avatar stops moving long before the tape ends — see the tape section above.

**Put the two windows side by side before you start.** The client launches `-windowed`
and the prompts print to the gamesrv terminal; you need to read one and act in the other.
Each step names itself, its duration and its prediction, then the next banner replaces it.
Do the action **once** and wait — a second attempt inside the same window is
indistinguishable from the first.

Nothing will answer you. That is by design (see the tape section above), so what you are
recording is what the client *asks for*, not what a completed action looks like.

Read it back with:

```bash
python toolkit/authsrv/labelrun.py --analyse
```

**Check the two idle rows first.** `idle_a` and `idle_b` predict silence; if either shows
traffic, the marks and the messages disagree and **no opcode from that run may be named** —
the tool says so and exits non-zero. Everything else in the report is only as good as
those two rows.

Steps that show nothing are a result, not a failure: the action was client-side, or it
needs a server reply to send its second message. The tool cannot tell those apart and
says so rather than guessing.

## The two run directories drift apart, and the loopback one loses

**Symptom.** The client dies on `Map.cpp(1762)` with `Map file '0x...' failed to
load. Attempting to re-bloat.` — the same assert whichever build hits it.

**Cause.** `run-live/` has its updater ENABLED (it must, or a live session cannot
stream map content), so a live run **writes new content into its own `Gw.dat`**.
`run/`, the loopback build, has the updater killed on purpose — the cage and the
patcher are in direct conflict — so it can never fetch anything and is frozen at
whatever `C:\gw` held when `make_run_dir.py` copied it.

The two archives therefore diverge the moment a live session visits somewhere new,
and **the divergence is invisible until something asks for the newer content**.
OBSERVED 2026-08-10: the R1.5 tape of Ascalon City carries `map_file_id 113021` in
its `0x0195`, `run-live/Gw.dat` resolves that id to MFT row **177262** and
`run/Gw.dat` resolved it to row **7982** — an older entry — so the loopback client
asked for content it did not have, could not fetch it, and asserted. Nothing was
wrong with the tape, the protocol or the server.

**Fix.** Give the loopback build the newer archive:

```bash
Copy-Item "C:\gd\Rurik\vault\run-live\<build>\Gw.dat" "C:\gd\Rurik\vault\run\<build>\Gw.dat" -Force
```

Two seconds on a warm cache, and **safe**: whose DH a build carries is decided by
`Gw.exe`, never by the archive, so this cannot move a build across the split that
`dhbuild.py` enforces. Run `python toolkit/clientpatch/dhbuild.py` after it and
expect "Every build is where it belongs."

**Check it worked** by resolving the id the crash named in both archives:

```bash
python -c "import sys; sys.path[:0]=['toolkit','toolkit/mapdata']; import archive; [print(p, archive.file_id_table(archive.Archive(p)).get(113021)) for p in (r'C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.dat', r'C:\gd\Rurik\vault\run-live\2026-07-29_221c13772c7a\Gw.dat')]"
```

Same row in both means the loopback client can load what the live one recorded.

## The third copy of Gw.dat, and why it exists

A running client holds an **exclusive lock** on the archive it was launched from.
While `Gw.exe` is up, `vault/run/<build>/Gw.dat` cannot even be opened for
reading — Python raises `PermissionError`, not a partial read — so any attempt to
study map data during a play session fails outright.

Rather than close the game every time, keep a copy that is never used to run
anything:

```bash
Copy-Item "C:\gw\Gw.dat" "C:\gd\Rurik\vault\dat_study\Gw.dat"
```

3.9 GB, about a minute. It is under `vault/`, so the provenance gate covers it —
`git check-ignore` confirms it, and it must never move anywhere else in the tree.

**Never launch a client against this copy.** Its whole value is that nothing ever
locks it.

Verify a copy by parsing its header, which cross-checks itself:

```bash
python -c "import struct; f=open(r'C:\gd\Rurik\vault\dat_study\Gw.dat','rb'); h=f.read(32); mft,=struct.unpack('<I',h[16:20]); size,=struct.unpack('<I',h[24:28]); f.seek(mft); m=f.read(16); cnt,=struct.unpack('<I',m[12:16]); print(h[:4], m[:4], cnt, size==cnt*24)"
```

Expect `b'3AN\x1a' b'Mft\x1a' 177335 True`. The last value is the check that
matters: the entry count sits in the MFT header and the table size sits in the
file header, and the two agree only if the 24-byte entry layout is right.

`C:\gw` is the owner's real install. Reading bytes from it is acceptable —
strictly read-only, nothing written, nothing copied into the tracked tree — but
it is never a target for patching or launching.

## Authoring terrain the client will compile

**RUN 2026-08-12 and it works** — FINDINGS 38. `vault/research/e3-terrain-2026-08-12/`
holds the twelve-step `RUNSHEET.md` with exact commands and the `PREDICTION.md`
that was recorded before anything was armed. Four things that run paid for,
worth having before you start another:

- **The authored stream must be SMALLER than its row's existing reservation** —
  and as of 2026-08-20 (WORLDMAPS-W1) both halves of the old escape clause are
  met: the compressor exists (`gwenc`, and `deploy.py --install` now writes the
  partner compression-8 by default, fit judged on the COMPRESSED size — a 96×96
  map fits where 32×32 was once the ceiling) and the relocation verb exists
  (`datmove`, taken automatically when even the compressed stream is too big).
  What stands: replace still never relocates, the reservation is still whole
  512-byte blocks, and a compressed install SHRINKS the row, so iterating from a
  small map to a big one relocates where it used to sit still (`grow_to` is the
  unwired fix, deliberately its own change). Historical: writing UNCOMPRESSED
  was what confined authoring to maps that shrink, and it killed the first
  design of that experiment outright.
- **`--exe` must be ABSOLUTE.** `session.py` hands it to `Popen` together with
  `cwd=`, and Windows resolves a relative program path against the *new*
  directory. The failure is a bare `FileNotFoundError` naming nothing.
- **Move `Gw.log` aside first.** The re-bloat line is the only evidence the map
  was reached at all, and a previous run's copy of it is indistinguishable from
  this run's.
- **The harness spawns no hostile unless you pass `--enemy`** (changed
  2026-08-12). `content/world.toml` puts the standing enemy 300 units from the
  player's arrival point and `AGGRO_RANGE` is 1200, so it used to engage on
  every session in every map — it killed the character 10 s into FINDINGS 40's
  movement session and cut two walk legs to 1.5 s. **Combat work must pass
  `--enemy`**; a `--probe` without it prints a warning naming the empty world,
  because a combat probe against nothing is a silent no-op. `authsrv.py`
  standalone is unchanged and still spawns it.
- **Judge on GEOMETRY, never on the trapezoid count.** FINDINGS 38's mesh went
  from covering the whole rect to covering 62% of it with its edge exactly on an
  authored cell boundary — and the count stayed at 2, in a chunk the same 419
  bytes. `rebloat.py --verify` prints the count, so its verdict line is not
  enough on its own.

## Rung E3: does the client ever compile a map?

**RUN TWICE, 2026-08-12, and the answer is YES both times.** FINDINGS 35: given a
zero-length Bloated stream the client logs, compiles the navmesh from the Stripped
partner and writes it back **byte-identical to what ArenaNet shipped**. FINDINGS 36:
given a Stripped stream belonging to a *different map*, it builds THAT map — so the
compiler's input is the bytes in stream 0 and nothing else. The procedure below is
what was run and is kept as the procedure; the only thing that has changed is that
its outcome is no longer open.

**The question it answered.** FINDINGS 34 established what the compiler *reads* by
reading x86. What nobody had established was that the shipped client ever *runs* the
converter. All 349 retail maps ship with both streams already built, so stage 2 might
have been pre-baked by ArenaNet's own tool with `0x00713630` dead weight in the
image. **This was the first experiment in the arc that could come back "no", and a
"no" would have been the useful result** — it would have collapsed E3 into authoring
the Bloated stream directly, which `mapbuild.py` already does.

**What is still open** is the run with terrain WE authored: both maps in those two
runs were ArenaNet's. `strippedterrain.build` (FINDINGS 37) is the missing half and
has never been through a client. That is `PLAN.md` §8 item 10 (e7).

**The trigger.** A zero-length stream-1 payload. FINDINGS 17.1 traced the
loader's `size == 0` branch at `0x00707749` straight through to the re-bloat
with no parse attempted. This is deliberately *not* the corrupt-chunk trigger:
C2's arm 3b fed the client a corrupt Bloated chunk and got an access violation
with no re-bloat attempt (FINDINGS 20.3), which is a different failure mode —
that crash happened during parsing, and a zero-length payload is never parsed.

**Target.** Map 143, file id `0x287D3` — row 71496 on `dat_study`, 9,284 B
Bloated, **27 trapezoids over 1 plane**, and its Stripped partner carries both
of FINDINGS 34's hard gates. It is already `content/maps.toml`'s map 143, so
the server can send the client to it. Fallback: map 144, `0x5D037`, 26
trapezoids.

### Before you start

The archive **must be a copy you can throw away**. `rebloat.py` refuses `C:\gw`
and `vault/dat_study`, but nothing stops you pointing it at a copy you care
about.

```bash
python toolkit/mapdata/datcheck.py --dat vault/dat_e3/Gw.dat --snapshot vault/research/e3/before.json
```

### 1. Plan (read-only, run it and read it)

```bash
python toolkit/mapdata/rebloat.py --dat vault/dat_e3/Gw.dat --file-id 0x287D3 --plan --baseline vault/research/e3/baseline.json
```

It prints the baseline mesh, confirms both hard gates are present, and refuses
outright if the map cannot answer the question. **The baseline JSON is what
makes a later "REBUILT" mean anything** — without it, "a Path chunk exists" is
satisfied by bytes we never deleted.

### 2. Arm

```bash
python toolkit/mapdata/rebloat.py --dat vault/dat_e3/Gw.dat --file-id 0x287D3 --arm --confirm --baseline vault/research/e3/baseline.json
```

Zeroes row 71496's whole 9,728-byte reservation, journalling every byte first.

**Then re-check the archive still opens legally** — this is measured to pass on
a built archive, but measure it on the real one too:

```bash
python toolkit/mapdata/datcheck.py --dat vault/dat_e3/Gw.dat --diff vault/research/e3/before.json
```

Exit 1 means CHANGED (expected — that is a result, not an error). Exit 2 means
the archive is too broken to have findings; **stop and revert if you see 2.**

### 3. Run the client

Standard three-terminal loop against our own server, caged, with the ours-DH
build. Travel to map 143 and let it load.

**Watch `Gw.log`.** The three strings that matter, all unguarded and so all
emitted if reached: `Attempting to re-bloat`, `Map '%s' failed to load`, and
`Map '%s' could not be opened for writing`. **Whether the map was reached at all
is a fact only the logs carry** — step 4 cannot tell "never loaded" from "loaded
and did not compile", and conflating those is the one way to draw a wrong
conclusion from this run.

### 4. Verify

```bash
python toolkit/mapdata/rebloat.py --dat vault/dat_e3/Gw.dat --file-id 0x287D3 --verify --baseline vault/research/e3/baseline.json
```

| outcome | means |
|---|---|
| **REBUILT** | the client compiles. Compare the trapezoid count against the baseline's 27 — a match means it reproduces ArenaNet's own build from the Stripped stream alone. A matching *count* is not a matching *mesh*; diff the payloads before claiming determinism. |
| **UNCHANGED** | still zero length. Read `Gw.log` before concluding anything. |
| **WRITTEN** | something is there that is not a map. Report it verbatim. |
| **RELOCATED** | expected, not a failure — see below. |

**The row will very likely move.** A reservation is `ceil(size/512)*512`, so a
zero-length row reserves nothing and the client's MFT-derived coalescing free
map is entitled to those blocks (FINDINGS 18.11). `verify` re-resolves by file
id for exactly this reason. Also run `datcheck --diff` and read the MFT
classification — relocation/recycle/delete/sibling-relink are the four shapes it
names, and a fifth is reported as UNCLASSIFIED rather than dropped.

### 5. Restore

```bash
python toolkit/mapdata/datwrite.py --dat vault/dat_e3/Gw.dat --revert vault/research/e3/rebloat_journal.json
```

Then re-cut the copy from `dat_study` anyway. `--revert` is byte-exact and
tested, but the client may have written elsewhere in the archive during the
session — it always does — and the journal only covers our own edits.

### What would make this run worthless

- Running it on an archive that already had a zero-length row (the plan refuses).
- Not reading `Gw.log`, so UNCHANGED cannot be attributed.
- Concluding "the compiler does not run" from a session where the client never
  reached the map.
- Treating a rebuilt Path chunk as proof the compiler would flood *our* terrain.
  It would not be: this map's Stripped terrain is ArenaNet's. That is the
  **next** experiment, and it only becomes worth running if this one says
  REBUILT.


## Killing something unattended (agent death, revive, loot)

Two flags, and without either the player never lands a hit. Found the hard way on
2026-08-13, after four runs blamed keybinds and input plumbing:

```bash
python toolkit/harness/session.py --enemy --keep-open   --game-args "--ping-seconds 0.5 --practice-target --explorable" --hold 30   --actions "0:play 20:vk:0x43 1:vk:0x20 25:vk:0x43 1:vk:0x20 25:vk:0x43 1:vk:0x20"
```

* **`--practice-target`** -- the standing hostile neither chases nor attacks. Without it
  the player LOSES: the Hatcher deals 25 into a 100 HP player (four hits) while killing
  it takes seven, so `hit agent` stays 0 because the player is dead. This is a real
  creature's behaviour, not a test switch -- WIKI (GWW, "Practice target",
  rev. 2014-02-07): stationary NPCs, allied and hostile variants, "They do not use any
  skills", slain hostile ones resurrect after 30 s at full health.
* **`--explorable`** -- an OUTPOST forbids attacking. In one the client selects a target
  (`0x00C1` goes out on every press) and no attack ever follows.

`0x43` is `C`, select CLOSEST target; `0x09` is `Tab`, select NEXT; `0x20` is `Space`,
attack. Three attack commands gave **21 hits and 3 kills in 30 s**, with the client's
attack arriving as `0x0026`.

The authentic Practice Target NPC is not in `content/npcs.toml` -- its model and name
string ids are not in the vault, and getting them means capturing a map that has one
(Isle of the Nameless, Churrhir Fields) and running `npcdefs.py` over it. What the flag
reproduces is its BEHAVIOUR, on the Hatcher's body, and the row says so.
