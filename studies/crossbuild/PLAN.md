# Cross-build resilience — what an ArenaNet update breaks, and what we do about it

**Plan, 2026-08-12. Supersedes the handoff note of the same day (`ec54c5a`).** That note
collected the question and was right about most of it, but it was written without running
anything. This pass ran things. Its §2 is carried forward **verified row by row**, its
census headline is withdrawn as unreproducible, two of its claims are refuted, and the
fix-first item has moved — because the worst breakage in the tree is not the one it named.

**The headline: `msgshape.py`, pointed at the older vaulted build, reports `cmd slots 0`,
prints `descriptor invariant violations: 0`, and exits 0.** It is the tool that reads the
client's own message-format tables, 25 hardcoded addresses feed it, `msghandler.py` and
`test_catalog.py` are built on it, it has no test of its own, and the two tests that do read
its numbers only ever run against the pinned build. That is a tool
returning a confident wrong answer about ArenaNet's client, which is exactly the defect
class §0 says this arc exists to hunt — and it was sitting one command away the whole time.

Results go to `studies/crossbuild/FINDINGS.md`. This file is the plan and gets struck
through as it lands.

> **THE UPDATE LANDED — build 38833, 2026-08-14. Results in
> [FINDINGS.md](FINDINGS.md) §7, and read that before re-quoting anything below.**
> The arc's tooling met a build nobody had measured and mostly held: **8 of 8 signatures
> at exact hit counts**, `msgshape`/`asserts`/`buildid`/`srctree`/`dump_dh_params` all read
> it, and the one class-(a) site this plan left outstanding — `genericvalue.py` — is the one
> that broke, taking `avevents.py` with it. It refused loudly and named the address, which
> is §6.1's hard-gate pattern working.
> **Three things below are now wrong and are corrected in FINDINGS §7:** §2's "any patch
> anchored to a raw address is broken by the next build" is **too strong** (this 15-day
> patch left the exe the same length and moved almost nothing — §7.2); the DH struct did
> **not** move this time, though its parameters rotated (§7.3); and `updatecheck.py`, this
> arc's own deliverable 8, **printed a vacuous pass about the new build** on its first real
> firing (§7.4a, fixed). The pin stays at **38797** — 38833 is registered, not pinned.
>
> **Landed 2026-08-12/13: every section — deliverables 1-8 complete, 9 ARMED.** §9 is the
> only one that cannot be finished on demand: it needs an ArenaNet content patch to land,
> and the trap is set with its prediction written down first ([DURABILITY.md](DURABILITY.md)).
> **The 38833 patch did NOT spring it**, exactly as §4 of FINDINGS predicted — the tracer
> sits on an inert copy no updater reaches. Nothing was lost; the owner's standing answer is
> to rebase mods over an update.
> `msgshape.py` derives the message tables (`db26a00`), `asserts.py` derives its callee
> (`458b79d`), `pinned.find()` verifies what it returns and fails closed (`25cd1c4`), the
> census is measured (`06bfcc3`), `genericvalue.py` is gated (`0a5b501`), `avevents.py`
> derives its allocators (`01e35df`), the build number is readable and the older build is
> **38519** (`b18f3ac`), and captures now carry a build stamp. Both vaulted builds come back
> clean from every tool in the arc.
>
> The measurements below are left in the past tense they were written in, because they are
> the evidence for why the work was done — not a description of the tree today.

**Labels** are [studies/character/FINDINGS.md](../character/FINDINGS.md)'s — OBSERVED,
UPSTREAM, RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND — plus
**MEASURED**: we checked real bytes on this machine ourselves. This arc leans on MEASURED
more than any other label, so it is declared rather than assumed.

**Client under study:** build **38797** (`vault/client/2026-07-29_221c13772c7a`,
10,483,904 B) against the older vaulted build (`vault/client/2026-04-30_b174de1f2d8d`,
10,404,032 B). Two samples, ~90 days apart, both post-Reforged. Every stability claim in
this document inherits that **n=2** and says so.

---

## 0. Scope, and what this is not

**In scope:** what stops working when ArenaNet ships a new `Gw.exe` and `Gw.dat` —
static-analysis offsets, the patcher, the wire schema, the map layer, the two run
directories, and whether a capture taken on build A can be read against build B.

**Not in scope:** the WASM pivot. `PLAN.md` §6:807 hedges this risk with "choose WASM: the
module bytes are the code and offsets come from the module", which is a strategic
re-platforming decision (§4, and §7 **Q2** at `PLAN.md`:1093 — *"Is the WASM client the
primary target? Recommendation: yes if Probe 3 passes"*). This arc does not get to make it
in passing. Assume the x86 client stays the target and cost the maintenance honestly; that
number is an *input* to Q2, which is most of why it is worth measuring.

**Also not in scope:** making anything survive a build change that currently fails
*loudly*. A test that goes red on a new build is doing its job. **The defect is a tool that
returns a confident wrong number** — and §3 is a live, measured example.

---

## 1. Before anything else, establish which tree you are in

```bash
git rev-parse --show-toplevel
```

This arc is a census. A census run in a stale worktree returns a confident number about an
old copy of the toolkit, which is the exact failure mode being investigated, one level up.
On 2026-08-11 a worktree was 33 commits and 42 `toolkit/` files behind `main` and nothing
errored.

Take a worktree under `.claude/worktrees/`, work in it, merge when the arc lands. Pin every
subagent to *that* path, require each command to begin `cd <tree> &&`, and have each agent
re-run the line above first and refuse on a wrong answer. For read-only fan-out,
`isolation: "worktree"` sidesteps the question. Recon fans out to Sonnet; the
classification calls in §6 stay on Opus/Fable.

**And stage by path.** Another session is usually live in the shared `C:\gd\Rurik` checkout.
`git add -A` there stages whatever anyone else has in flight — that is how this very file
was swept into an unrelated commit and had to be untracked again (`4d5799b`).

---

## 2. What is already established — do not re-derive any of this

Every row below was re-checked against the tree on 2026-08-12. Line numbers are live as of
that date.

| Claim | Label | Where |
|---|---|---|
| The update happened *to us*: `Gw.exe` 10,404,032 → 10,483,904 B, `Gw.dat` replaced, DH struct RVA `0x6843e8` → `0x6910d8`, **both the prime and the server's public key changed** | MEASURED | `PLAN.md`:803; primary source `studies/handshake/PLAN.md` §0.4:78-105 |
| ArenaNet rotates DH per build — Headquarter stores 107 server keys rather than one constant | UPSTREAM, corroborating | `PLAN.md`:803 |
| Six byte-shape signatures each reproduced their **exact hit count** (1/1/1/1 and 4/2) across the ~90-day gap, while VAs drifted **non-uniformly**. `.text` grew 44,032 B | MEASURED, n=2 | `studies/profession/WORKAROUNDS.md` §3.5:410, paras :425-431 |
| **Any patch anchored to a raw address is broken by the next build; byte-shape anchoring survived both samples.** n=2 is induction, not a guarantee | MEASURED / stated limit | ibid. :432-433 |
| In-place code ceiling is **78 bytes** — largest contiguous `int3` run in 5,471,232 B of `.text` (146,527 int3 bytes, 26,243 runs, 8 are ≥40, zero reach 100; the older build: 144,620 / 25,598 / 7 / 0 / **47**) | MEASURED, both builds | ibid. :435-440 |
| Source-path census reproduces: 937 paths on 38797, 936 on `2026-04-30`; six spellings of "Server", zero hits, both builds | MEASURED | `test_srctree.py`:48-52 (the build/count pairs), :123-125 (the census), :127-130 (the six spellings); patterns at `srctree.py`:63-70 |
| The `CHAR_PROFESSIONS` census reproduces 29 sites / 13 files on both builds with relocated bases | MEASURED | `studies/profession/FINDINGS.md`:249 |
| `MOVE_TO_COORD` is `0x003C` in GWCA's older client and `0x003E` in ldufr's and ours — **opcodes are not stable across builds.** Read the limit: the drift is corroborated by two upstreams on either side of it, *not* measured across our two vaulted builds, and `0x003C` has never appeared in a capture of our own | CORROBORATED (ldufr + GWCA); only "`0x003E` works on 38797" is OBSERVED | `studies/movement/FINDINGS.md`:430, framing at :435-438 |
| A `Gw.dat` write survives a full play session unrepaired; the allocator relocates rows, but has only ever been observed doing it to the client's own scratch rows (8315/8316 moved, 8315 grew 92 → 96 B) | MEASURED, n=2 | `studies/datwrite/FINDINGS.md` §6:1604-1607; the "survives a full session, unrepaired" phrasing is §8's summary at :1642 |
| An MFT row index is meaningful only against the archive copy it was measured on; **file ids are the portable key** | design, enforced | `toolkit/mapdata/mapchunks.py`:117-121 |
| The two run directories diverge the moment a live session visits somewhere new, and it is invisible until something asks for the newer content: Ascalon City `map_file_id 113021` → row **177262** in `run-live/`, row **7982** in `run/`, and the loopback client died on `Map.cpp(1762)` | OBSERVED 2026-08-10 | `RUNBOOK.md`:740-742, figures at :753-756 |
| Nobody has costed the total build-coupled surface. The register names: the message-table VAs, the assert VA, the DH struct RVA, skill-table row count 3,443, the area table, the generic-value VAs, and `CENSUS_38797` | the *shape* is MEASURED; two of its numbers are not — see the row below | `studies/review/FINDINGS.md` §1c:579-585, figures at :581 (repeated at :205) |
| **Two figures in that register do not reproduce and are carried as inherited, not measured.** `:581` gives "26 message-table VAs" — the true count is **25** (`msgshape.py`:76-94, corroborated by `studies/msgtable/FINDINGS.md`:42 "751 messages are registered across 25 tables"). It also gives "30 addresses in `toolkit/`, 75 in `studies/`" with no stated counting method, and no scope tried this session lands near either | UNVERIFIED, and deliberately not re-derived here | ibid.; the correction is deliverable 4's job, not §2's |

Four guards already exist and are the pattern the rest should follow:

- `content.py` refuses a `source = "client-table"` row with no `build` (`NEEDS_BUILD` at
  :121, enforced at :280-288), on the rationale stated at :114-116 — a table read out of
  `Gw.exe` "is a fact about THAT BUILD and moves when ArenaNet ships";
- `mapchunks.py` stamps its cache with the archive copy it was built from and **drops** it
  rather than trusting it when the stamp disagrees;
- `pinned.py` names which `Gw.exe` a tool read and why, because the vault holds two copies
  of 38797 that are **the same length and differ in 144 bytes** — nine of them in `.text` —
  so a size guard cannot tell the pristine copy from our patched one;
- `authsrv.py`:100-107 is the worked example of surviving a drift *well*. Upstream said the
  game version header was `0x000C0700`; build 38797 measured `0x000C0500` **on the wire**.
  The fix widened `GAME_VERSION_HEADERS` into a tuple and rejects-and-logs an unknown header
  (`handle()`, :3128) rather than replacing one constant with another. Graceful degradation,
  already shipped, already correct.

---

## 3. ~~Fix first: `msgshape.py` returns a confident falsehood on any other build~~

✅ **LANDED 2026-08-12, `db26a00`.** *(estimated "days"; it took one session, and the
estimate is scored here rather than quietly dropped — the derivation route was already
written down in the module's own comment, which is most of why.)* On the older build:
25 tables, 751 declared entries, 666 messages, 2,417 cmd slots, **0** entries lost to the
unmapped skip, four oracles PASS against its own AgMsg table at `0x00A466A8`, and
invariants 0 over 1,751 real descriptors. 38797 reproduces `CENSUS_38797` bit for bit.
`msgshape.py 0x00E5` now decodes on the older build — same shape, that build's address.

**Prediction, stated before the run** (house rule): pointed at the older vaulted build,
`msgshape.py` would either refuse loudly, or return a confident census differing from
`CENSUS_38797`. **MEASURED 2026-08-12, and the outcome was worse than either.**

Control, build 38797:

```
cmd slots 2420, statically present 1321, zero in file 1099, recovered 1097, unaccounted 2
  oracle 0x001E  PASS      (and 0x0020, 0x0029, 0x002C)
  descriptor invariant violations: 0
```

The same command against `vault/client/2026-04-30_b174de1f2d8d/Gw.exe`:

```
cmd slots 0, statically present 0, zero in file 0, recovered 0, unaccounted 0
  oracle 0x001E  FAIL
    got []
  oracle 0x0020  FAIL
  oracle 0x0029  FAIL
  oracle 0x002C  FAIL
  descriptor invariant violations: 0
EXIT=0
```

Three separate defects, and the third is the one that makes this fix-first:

1. **`descriptor invariant violations: 0` is vacuous.** Zero descriptors means zero
   violations. This repo's own law — *a check that cannot fail is not a check*, *a run that
   measured nothing failed* — is being broken by a live tool, in a line that reads as a pass.
   MEASURED by instrumenting `invariants()` (:370-391): build 38797 examines **666 messages
   and 1,754 descriptors**; the older build examines **0 and 0**. Both print the same line,
   byte for byte.
2. **`CENSUS_38797` is never asserted against inside the tool.** The constant sits at
   `msgshape.py`:100 documenting what a healthy run looks like, and nothing compares 0 to
   2,420. `test_catalog.py`:131 does the comparison — but see §10, it cannot be pointed at
   another build.
3. **It exits 0.** The oracle lines say FAIL four times; the process says success. There is
   **no `test_msgshape.py`** — `studies/review/FINDINGS.md`:585 already called this "the
   cheapest gate in the repo… left un-wired". Two suite tests *do* read these lines
   (`test_catalog.py`:131-134, `test_skillcast.py`:344-350), but both resolve their client
   through `pinned.find()` and therefore only ever run against 38797, so **nothing reads
   them on any other build** — which is the only build on which they can go red.

And the single-opcode path does not print an empty census, it makes a **claim about
ArenaNet's client**:

```
$ msgshape.py 0x00E5 --exe <older build>
opcode 0x00e5 is in no table on this build          (stderr)   EXIT=1
```

That claim is false — the opcode is there; our 25 addresses are not. Note the exit code
honestly: this path is the one place in the tool that already fails loudly, via
`sys.exit(<str>)` at :448, which prints to stderr and exits 1. **The defect here is the
message, not the exit status.** A reader is told a fact about the client when the truth is
a fact about our table, and no exit code can carry that difference.

**Blast radius.** `TABLES` (`msgshape.py`:76-94) is **25 entries, 25 distinct VAs, 751
declared descriptors** — MEASURED, and corroborated by `studies/msgtable/FINDINGS.md`:42
("751 messages are registered across 25 tables"). `studies/review/FINDINGS.md`:581 says 26,
repeated at :205; both want correcting. It is imported unchanged by `msghandler.py`:64 and
**duplicated** in `test_catalog.py`:61 (`AUTH_RECV_TABLES`), so the same addresses are pinned
in two files. Downstream sit the 477/477 catalog agreement and `msghandler.py`'s "477 of 477
carry a non-null dispatch", which is the loopback opcode sweep's stated prediction. The
comment above `TABLES` has said so all along (:73-75): *"a different build moves every one of
these."*

**Do:** re-derive `TABLES` rather than storing it. The route is already written down in the
same comment block (:74) — the tuple was recovered "from the 14 callers of
`MsgChannel::RegisterMsgs` at VA `0x007de010`". Anchor `RegisterMsgs` by byte shape, find its
call sites by scanning
for the call idiom (the `asserts.py` call-site scan is the model, and it is stdlib), and read
the table VA and entry count out of each site. `msgshape.py` keeps its deliberate
no-disassembler stance: carve-out (1) covers `msghandler.py` and `codescan.py` only, and this
recovery does not need it.

**Acceptance.**

- On **both** vaulted builds, `msgshape.py` either resolves the tables and reproduces its
  oracle set, or **refuses with a non-zero exit**. A zero-slot census is a refusal, never a
  report.
- `descriptor invariant violations: N` may not be printed as a pass over zero descriptors.
  The check declares how many descriptors it examined.
- `test_msgshape.py` exists, is named in `CLAUDE.md`'s suite list **in the same commit**, and
  declares a `floor` set from a real green run. Its load-bearing check is the older build,
  because that is the one that can go red for the right reason.
- The pinned `TABLES` tuple is kept as a **cross-check that prints when it disagrees**, not
  as the lookup — same demotion §4 applies to `ASSERT_VA_38797`.

---

## 4. ~~Second: `asserts.py`, de-pinned~~

✅ **LANDED 2026-08-12, `458b79d`.** *(estimated "hours", and it was.)* Both builds return
`single-routine=True`, one distinct callee, no warning. The callee is derived twice —
consensus over ~19,700 call sites (one distinct target, 100.0000%, both builds) and a
27-byte signature — and the two must agree or it refuses. `test_codescan.py` §10 is the
both-build section, asserting the shape counts.

`toolkit/clientscan/asserts.py`:111 carries `ASSERT_VA_38797 = 0x00487BC0` and uses it live
at :317 (`callee = self.base + (ASSERT_VA_38797 - 0x00400000)`). Against
`2026-04-30_b174de1f2d8d` it reports 19,680 sites — 19,544 edx-first, 74 ecx-first, 62
shared-tail, so **all three call shapes are present on both builds** — with
`single-routine=False` and its own warning (`main()`, :530-536). `studies/srvtree/FINDINGS.md`
:262-268: *"the older build's assert corpus is not currently trustworthy, and that is worth
fixing before anyone leans on it."*

This is not cosmetic. `asserts.py` supplies the module ranges `codescan.py --in` narrows
searches to (`_asserts()` :411-417, `module_bounds()` :420-440, CLI wiring :490-491 and
:518-521), and `asserts.py`:384 names that dependency itself. §8 and §9 of `test_codescan.py`
exist because an under-counting assert scan already produced two report rows that described
no file in the image. **An under-count propagates silently into every search run inside it.**

**Do:** locate the assert callee by byte shape rather than by VA. The routine every assert
site calls has a prologue, and all three call shapes are present on both builds, so the
anchor exists on both. Keep the pinned VA as a *cross-check that prints on disagreement*,
never as the lookup.

**Acceptance:** `asserts.py` returns `single-routine=True` with no warning on **both**
vaulted builds; `test_srctree.py` and `test_codescan.py` stay green; a both-build section is
added to `test_codescan.py` with the three shape counts as the assertion.

---

## 5. ~~`pinned.find()` fails open, and twelve tools trust it~~

✅ **LANDED 2026-08-12, `25cd1c4`**, and it went first because §3's and §4's acceptance is
"on **both** vaulted builds" and `pinned.py` did not know a second build existed. *(hours,
as estimated.)* `find()` hashes what it returns and refuses; the live install is opt-in;
`BUILDS` is the registry and `test_srctree.py` reads its stamps from it.
`test_pinned.py`, 41 checks.

`pinned.py` was built to be the single answer to "which `Gw.exe`", and it half is.
`identify()` (:98-111) is a real check — size gate, then sha256 against `PRISTINE_SHA256`
and `PATCHED_SHA256`, returning `pristine` / `patched` / `unknown`. **`find()` (:114-133)
never calls it.** It tests `os.path.isfile` and returns. `identify()` is invoked from
`pinned.main()` (:147, :150) and two tests (`test_cage.py`:69, `test_skillcast.py`:313) —
nowhere on the path any analysis tool actually takes.

Worse, `find()`'s third fallback is `C:\gw\Gw.exe` — the owner's **auto-updating install** —
returned with `why = "live install -- auto-updates, so it may not be 38797"`. The string is
honest and it is the entire control. Nothing refuses.

So every tool in `toolkit/clientscan/` that resolves its client through `pinned.find` — all
twelve of `asserts` (:107), `avevents` (:121), `codescan` (:168, spelled `_pinned.find`),
`genericvalue` (:84), `msghandler` (:72), `msgshape` (:71), `areatable` (:111), `skilltable`
(:49), `textrec` (:150), `argtable`, `protoscan`, `srctree` — can run build-38797 addresses
against an unknown build, and the only thing standing between that and a published number is
a human reading a line of output. A thirteenth consumer sits outside that directory and is
build-sensitive for the same reason: `toolkit/harness/dryrun_keycapture.py`:368-371, which
feeds the VA-dependent key-tap path. This is the same shape as the `.gitignore` and
derivation-register failures: *a rule nothing checks is a wish.*

**Do:**

1. `find()` verifies before returning, and a VA-dependent caller gets a **refusal** rather
   than the live install. Reading the live install stays possible, but only when asked for
   explicitly.
2. Teach `pinned.py` that **more than one build exists.** Today it has no notion of
   `2026-04-30_b174de1f2d8d` at all, which is why `test_srctree.py`:48-52 hardcodes its own
   `BUILDS` list — the only genuine cross-build test in the tree, with no shared helper under
   it. That list belongs in `pinned.py` so §3's and §4's both-build sections can use it.

**Acceptance:** a tool asked for the pinned client against a vault that does not hold it
refuses instead of silently reading `C:\gw`; `test_srctree.py`'s `BUILDS` list has one home;
a negative control proves the refusal can fire.

---

## 6. ~~The census — and the trap inside it~~

✅ **LANDED 2026-08-12.** `toolkit/buildpins.py` + `test_buildpins.py` (40 checks), results
in [FINDINGS.md](FINDINGS.md) §1-§2. **68 class-(a) sites across 7 files** — 26 converted,
5 accepted, 37 outstanding in three jobs. `PLAN.md` §6:803's "ongoing" is replaced. The
"409 across 49" headline below is withdrawn in the text that follows, and
`studies/review/FINDINGS.md`'s 26/30 are corrected at :205 and :581. The trap was real and
is now measured: prose citations outnumber live constants **360 to 68**, so a grep-built
census would have been 84% noise.

**The handoff note's "409 occurrences across 49 `toolkit/` files" is withdrawn.** It does not
reproduce under any reading of the regex tried. Stating the method, because the whole point
of this section is that a number without one is not refutable — `\b0x[0-9A-Fa-f]{8}\b` over
every `*.py` under `toolkit/`, `__pycache__` excluded:

| Scope | Occurrences | Matching lines | Files |
|---|---|---|---|
| strict word boundary | 890 | 742 | 75 |
| same, excluding `test_*.py` | 571 | 468 | 43 |
| substring-tolerant | 891 | 743 | 76 |

The tolerant/strict gap is a single false positive — a 16-hex-digit literal in
`test_dhbuild.py`:311 — so the pattern is not the source of the disagreement with 409.
Rather than mint a fourth number, adopt the register in §2 and let deliverable 4 re-derive
the two figures §2 flags as unreproduced.

The counting was never the deliverable anyway. **Classifying is.** This repo cites addresses
in prose constantly, and a citation is provenance, not a liability. Three classes, three
verdicts:

| Class | Example | Verdict |
|---|---|---|
| **(a) Live constant** the tool computes with | `ASSERT_VA_38797` (`asserts.py`:111), `TABLES` (`msgshape.py`:76) | Per-build liability. Convert to a signature (§7), or gate it behind a build check that **refuses**. |
| **(b) Citation in a comment or docstring** | `agents.py`:85-97, `genericvalue.py`:86-89 — where a finding came from | Harmless and **wanted**. Must carry its build id in the same breath; a bare VA with no build is the defect, not the VA. |
| **(c) Test expectation** | `test_skillcast.py`, `test_codescan.py`, `test_catalog.py`'s `CENSUS_38797` check | **Wanted.** Going red on a new build is correct. The requirement is that the failure *says so* — "this address is from build 38797 and you are reading N" — rather than reading as an ordinary bug. |

**Use the syntax tree, not a grep.** A grep cannot tell a docstring from a constant, and this
repo has been bitten twice by exactly that substitution: `test_cmsgnames.py` had a grep that
asserted its own arm's formatting and reddened on a line break, and `sweeploop.py`'s cage
check hit the docstring explaining the rule. `test_srclint.py` and `test_dispatch.py` both
already walk `ast` and are the models.

### 6.1 Class-(a) sites already found, ordered by severity

This is the census's starting state, not its finish. Every row is MEASURED 2026-08-12.

| Site | Symbol | Anchors | Guarded? |
|---|---|---|---|
| `itemprobe.py`:73-74 | `RVA_TLS_INDEX` (`0x00C0F300`) | TLS index read from a **live client process** (:298) | **No — and it does not import `pinned` at all.** Only a plausibility bound on the result (:300-302). |
| `agentprobe.py`:46-48 | `RVA_ARRAY` (`0x00BF96CC`), `RVA_COUNT` (`0x00BF96D4`) | live agent array base and count (:102-103) | **No.** Same — no `pinned`, no build provenance. Bound at :106. |
| `msgshape.py`:76-94 | `TABLES`, 25 VAs | every RECV/SEND descriptor table | **No.** Two silent `continue`s swallow it (:265-268) — and MEASURED on the older build, the dominant one is the unmapped/zero `cmds_va` branch at :265-266 (**651 of 751**), not the bad-count branch at :267-268 (100 of 751). §3. |
| `msghandler.py`:64 | imports `TABLES` unchanged | handler dispatch lookups | inherits the above |
| `test_catalog.py`:61 | `AUTH_RECV_TABLES` | two of the same VAs, duplicated | class (c), but duplicated rather than imported |
| `asserts.py`:111 | `ASSERT_VA_38797` | expected assert callee | **Soft** — guard at :535, warning at :536, does not exit. §4 |
| `avevents.py`:125-127 | `ACTION` (`0x007F2E90`), `EFFECT` (`0x007F5340`) | AgentView event allocators | **Soft** — `--census` reports, never raises |
| `genericvalue.py`:90-109 | 5 switch dicts | jump-table switches read as data | **Partial** — raises if an index leaves the *derived* table (:208-210), but the VAs themselves are never verified |
| `genericvalue.py`:119-127 | `CHAINS` | 2 compare-chain switches | **Yes, hard** — byte `verify` at the VA, raises on mismatch (:228-234). **This is the model.** |
| `genericvalue.py`:131 | `MAIN_SWITCH_GATE` | the gate before each main switch | **Soft** — prints "MOVED -- results are suspect" (:346-348) |

**The two live-memory readers are the top of this list on purpose.** Every other row produces
a wrong *number*. `itemprobe.py` and `agentprobe.py` dereference a hardcoded RVA inside a
**running client**, so on a new build they do not compute a wrong answer — they read
arbitrary memory. They are also the only two class-(a) sites with no build provenance of any
kind, not even a printed `why`.

**Deliverable:** the finished table in `FINDINGS.md`, one row per class-(a) site, each with a
**converted / gated / accepted** verdict and the cost of conversion. That table *is* the
maintenance number `PLAN.md` §6:803 currently records as "ongoing", and it is the input §7 Q2
has been missing.

### 6.2 The toolkit already contains its own best answer

Worth writing down, because it reframes the work as *finishing* rather than *inventing*:
`areatable.py`, `skilltable.py` and `textrec.py` all locate their targets **structurally** —
multi-constraint scans, or two independent locators required to agree — with explicit
comments that hardcoding the address would be wrong. `areatable.py`'s docstring frames its
two-locator agreement as "a check that cannot fail is not a check". The class-(a) sites are
the places that did not get that treatment, mostly because a compare chain or a TLS slot has
no obvious structural fingerprint the way a table of records does. Some genuinely may not be
convertible; those get **gated**, and the census says so rather than pretending.

---

## 7. ~~Conversion — signature anchoring, and the two rules that make it safe~~

✅ **LANDED 2026-08-13**, results in [FINDINGS.md](FINDINGS.md) §6. `SIG_KEYS` had three
implementations with three policies; there is now ONE (`dhbuild.locate_keys`) and two call
sites, and the bytes are re-exported rather than re-typed. §7.2's two signatures exist in
code, in `toolkit/clientscan/sigcorpus.py` — the corpus is **eight signatures, all
reproducing their exact hit counts on both builds** while every address moved.

The pattern is proven and already in the tree: `SIG_KEYS`, `SIG_MUTEX`, `SIG_DOWNLOAD` and
`KEY_TAP_CAVE_SIG` in `toolkit/clientpatch/dhbuild.py`, `TAP_SIG` in `keytap_patch.py`,
`SIG_KEYS` again in `dump_dh_params.py`.

Two rules, both load-bearing:

1. **A signature must be unique in `.text`, and the tool must refuse on 0 *or* 2+ hits**
   rather than taking the first. Taking the first hit is how a tool keeps returning a number
   after the thing it was looking for moved.
2. **Encode protocol constants and stolen prologues, not addresses** — the bytes that have a
   reason to stay put. `keytap_patch.py`:23-25 states this explicitly and is the reference
   (the decisive clause is at :24: protocol constants "unlikely to move across a rebuild —
   the stolen prologue, the 20-byte key length, the RC4 setup"), with the
   never-hardcoded-to-an-address statement at :4-7.

`keytap_patch.py` honours both, in both places: `_find_tap()` raises on 0 (:81-85) and on 2+
(:86-88) and cross-checks the six stolen bytes (:90-93); `locate_slot()` does the same
(:217-220).

### 7.1 The first conversion is a rule already broken three ways

**MEASURED:** the *same* `SIG_KEYS` byte pattern carries three different policies in three
files that all bear on the same DH-key safety decision.

| File | On 0 hits | On 2+ hits |
|---|---|---|
| `dhbuild.py`:122-155 | raises (:124-129) | **raises when the hits resolve to *different* DH-shaped structs** (:148-154), refusing to guess which one the client reads. Duplicate hits pointing at the same struct are accepted (:155), and a third refusal at :141-147 covers hits with no DH-shaped target — so the guard is on the resolved struct, not on the match count |
| `make_custom_client.py`:137-152 | raises (:139-143) | **takes the first**, printing "note: N accessor matches; using the first" (:144-145) |
| `dump_dh_params.py`:136-186 | exits 2 (:138-142) | **no check at all** — iterates every hit and reports each |

`dhbuild.classify()` is the one `cage.py`'s launch gate trusts and it is fail-closed, so the
safety-critical path is sound. But `make_custom_client.py` is **the patcher**, and
`dump_dh_params.py` is the go/no-go a human reads before trusting any patching tool against a
new build. Rule 1 should hold in all three. This is the cheapest possible first conversion
and it fixes a real inconsistency rather than a hypothetical one.

### 7.2 Two free signatures

`studies/profession/WORKAROUNDS.md` §3.5 derived two signatures from scratch that exist in no
code — VERIFIED absent from `toolkit/` this session: the attribute accessors (4 hits) and the
`imul`-stride colour tables (2 hits). Both reproduced their exact hit counts across the gap.
Landing them costs little and doubles the corpus of shapes we have re-verified.

**Do not report "signatures are stable".** It is n=2 induction over one build gap and the
study says so. The claim this arc can support is: *address anchoring failed on both samples,
shape anchoring survived both.*

---

## 8. ~~Build identity — the primitive that does not exist~~

✅ **LANDED 2026-08-13**, results in [FINDINGS.md](FINDINGS.md) §4. `toolkit/clientscan/`
`buildid.py` + `test_buildid.py` (23 checks). **The older vaulted build is 38519** — a
number this project had never been able to write down. The prediction below was half
refuted in advance and half correct, exactly as written: the version resource is useless,
and the embedded literal is there — the client compiles its build as a whole function,
`mov eax, <build>; ret`, and exactly one such getter per image carries a five-digit value.
`pinned.BUILDS` now carries both numbers and `test_buildid.py` §4 requires them to match a
fresh read, so they are derived rather than typed in.

**NOT FOUND: anything in this repo derives a BUILD NUMBER from a `Gw.exe`.**
`pinned.BUILD = 38797` is a hand-written constant. Build identity on disk is a date plus a
sha256 prefix (`STAMP`), and `identify()` compares hashes, never a version field. The
consequence is concrete and slightly absurd: **the older vaulted build's numeric id appears
nowhere in the tree.** It is only ever `2026-04-30_b174de1f2d8d`.

One exe-side version reader does exist and is worth knowing about before anyone writes a
second: `toolkit/snapshot_client.py`:80-92 `version_info()` shells out to PowerShell for
`(Get-Item path).VersionInfo` and records `FileVersion` / `ProductVersion` into the snapshot
manifest as `gw_exe_version` (:115).

From the **wire**, the build is readable in three independent places:

| Where | What it does |
|---|---|
| `authsrv.py`:3140, :3156 | records `build=` on a `version` event, both channels, unpacked from the client's own VERSION frame |
| `tape.py`:522-550 (`client_version`) | parses build / world / map / player from a raw `wire.jsonl`, from the **client's** first bytes rather than anything we wrote |
| `webgate.py`:92-100 | reads `User-Agent: Gw/38797.0 (Win32)`, in the clear — "the cheapest build stamp available and every capture wants it" |

So the fact is available and un-plumbed. Until an exe-side reader exists, "stamp every
artifact with its build" (§10) is unsatisfiable for half the corpus, and the arc cannot even
name the build it is comparing against.

**Deliverable:** a build reader for a `Gw.exe`, then §10's stamp.

**Prediction, and half of it is already refuted — by evidence that was sitting in the vault,
written by our own snapshotter.** The obvious guess is "the version resource carries it".
**REFUTED, MEASURED 2026-08-12:** both vaulted manifests report `gw_exe_version` =
`FileVersion '1, 0, 0, 1'`, `ProductVersion '1, 0, 0, 1'` — **identical across the ~90-day
gap**, and identical to four sibling DLLs that did not change at all. The version resource is
not a build discriminator and never was. The only field in either manifest that separates the
two builds is `pe_timestamp_utc`: `2026-04-30T22:17:11Z` against `2026-07-29T22:59:45Z`.

So the open half is narrower and should be stated that way: **is the build number present as
an embedded literal in `.text`/`.rdata`?** It is plausible, because the client puts `38797`
on the wire in its VERSION frame and in its own User-Agent, and something has to source it.
Predict: yes, findable, and cross-checkable against the wire value we already record. **If
NOT FOUND, that is a first-class finding** — it would mean build identity is observable only
by running the client or watching the wire, and a purely static pre-update snapshot can never
capture it. `pe_timestamp_utc` would then be the honest fallback discriminator, and it should
be labelled as what it is: a distinguisher, not a build id.

---

## 9. ~~`Gw.dat` across an update~~ — ARMED 2026-08-13, not done

✅ **ARMED**, and it cannot be finished without an ArenaNet content patch.
[DURABILITY.md](DURABILITY.md) is the trap and states its prediction first, per the house
rule. `vault/dat_durability/Gw.dat` carries a journalled, reverted-and-re-armed tracer in
row 46196; the archive still passes all ten open-time rules; revert was PROVEN against the
real archive rather than a fixture.

**Two corrections to the plan below, both found by trying to do it.** Step 4, "let the
update land on that copy", **cannot happen** — the updater updates the archive the client it
belongs to opens, and an inert vault copy is never that. DURABILITY §2 names the three
routes and the one that needs an owner decision. And step 5's classification has an
instrument problem: `datcheck` labels an in-place content change `new extent (silent
relocation)` when nothing relocated (DURABILITY §3.2).

**The retroactive half was then RUN** (2026-08-13, DURABILITY §5), and it did more than
characterise the update. **334 of 177,311 rows changed, 0 unclassified** — Tier 1's vocabulary
covered every one. But two adversarial passes refuted what that seemed to mean: 0.19% is the
fraction of ArenaNet's LIVE rows disturbed, and an authored row lives in the SCRATCH
resources, where the rate is **79.70% by free block and 2 of 2 by claimable row slot** — the
update recycled row 35300, the exact slot `datplan.plan_insert` claims. And the trap as armed
**could not have read its own result**: `datcheck` prints 40 rows and the tracer sorts at
~301, while "relocated" and "overwritten in place" produce identical output. Both are fixed
or recorded; the prediction's reasoning is refuted in DURABILITY §4b.

What is known is §2's row: a write survives a *play session*. What a **content patch** does
to an authored row has never been measured, and the two questions that depend on it are both
parked:

- **Is a custom area durable or per-build?** — `studies/customarea/FINDINGS.md`:756, :1229,
  :1952, asked three times. **Correction to the handoff note:** it is not wholly unanswered.
  :1954 partly closes it *in the study's favour* — a second-build check found an identical
  struct layout at a relocated VA — but :1961 states the accepted **chunk versions were not
  re-checked and remain the open half.** That open half is the decisive one.
- The **29 of 171,025 file ids carrying bit 31** are a stale/needs-refresh watchlist the
  client cleared on two entries in one session. `studies/datwrite/FINDINGS.md`:589 calls it
  "one more durability signal nobody has pulled on".

**The experiment cannot be run retroactively**, which is why this document exists now rather
than after the next update. It needs a *before* state:

1. Copy the archive to a scratch path (never `C:\gw`, never `vault/dat_study` — both refused
   by the write guards, each with a positive control that an ordinary copy is allowed).
2. Arm a known write with `datwrite.py` — journalled and reversible — and record the row, its
   reservation and its checksum.
3. Snapshot: `python toolkit/mapdata/datcheck.py --dat <copy> --snapshot before.json`
4. Let the update land on that copy.
5. `python toolkit/mapdata/datcheck.py --dat <copy> --diff before.json` and classify every
   change by FINDINGS 18.5's Tier 1 shapes — relocation, recycle, delete, sibling relink, or
   **UNCLASSIFIED**.

**Exit codes, VERIFIED** (`datcheck.py`:101-104, :644-659, :704-715): `--preflight` 0 clear /
1 failed; `--diff` **0 byte-identical / 1 something changed, which is a RESULT / 2 the run
could not be made.** Do not conflate 1 and 2 — that distinction already cost a crash being
reported as "the row moved".

**Predict first** (house rule): state, in writing, before step 4, whether you expect the
authored row to survive, be relocated, or be overwritten — and what each outcome implies for
the E3 and custom-area routes. A probe with no stated expectation can be rationalised into
agreeing with anything afterwards.

---

## 10. ~~Captures and schema — one built story, one real gap, two corrections~~

✅ **LANDED 2026-08-13**, results in [FINDINGS.md](FINDINGS.md) §5. `origin.py` carries
`build_of` / `require_single_build`, checked against the file's own contents and
three-valued like the origin stamp; `test_movement_fidelity.py` calls it;
`livesession.py` stamps the build it parses from the client's own VERSION frame, closing
the format gap `tape.py` documented; `overrides.json` gained a structured
`validated_against_build`. **The UNVERIFIED flag below is answered: no corpus figure pools
builds** -- every capture in the vault that names one names 38797 (1,122 files), and
`test_origin.py` now asserts that as an invariant.

**The schema half is mostly built; do not re-invent it.** `schema/messages.json`:8 carries
`"validated_against_build": 38797`. `PLAN.md` §4 A3:700 already states the law — *"Every
schema revision must carry a client build id. `MOVE_TO_COORD` drifted `0x003C` → `0x003E`
between builds, so an unstamped catalog is not merely stale, it is actively dangerous."* On a
new build the move is to stamp a **new** schema revision, never to edit in place.

**Correction 1.** The handoff note said `overrides.json` "records which arbitrated it".
**REFUTED:** `schema/overrides.json` has no `validated_against_build` key at all. Its
top-level keys are exactly `provenance` and `channels`. 38797 appears six times and every one
is free text — twice in the top-level `provenance` string and four more in per-override `why`
strings — so nothing can check any of them. Giving it a structured, checkable key is a
five-minute deliverable.

**Correction 2.** The handoff note said `test_catalog.py` *is* the re-validation instrument —
"on a new build, point it at the new exe, diff, and stamp a new revision". **REFUTED as
written.** `test_catalog.py` has no `argparse`, no `--exe`, and no environment override; it
calls `pinned.find()` (:123), which resolves one hardcoded `STAMP`. What it *does* do is
assert `census == MS.CENSUS_38797` (:131-132) and pin `EXPECT_SHARED = 477` (:52-56), so it
will go **red** on a new build — correct class-(c) behaviour, and worth keeping exactly as it
is. But red is not the same as re-validating. **Pointing it at a new build is not currently
possible**, and §5's build selector is the prerequisite. `pinned.py`:54 claims "every tool
here can `--exe` past it"; `test_catalog.py` is one that cannot — and so are `argtable.py`
and `protoscan.py`, which have no `argparse` at all and call `pinned.find()` at import time
(:11 and :21).

**The gap is captures, and it is a HANDOFF-day-one constraint gone unenforced.**
`HANDOFF.md`:237 says "record the build id in every capture manifest". `toolkit/origin.py`
stamps *whose server* produced a capture — three-valued, ours/live/unknown, with `UNKNOWN`
deliberately not a synonym for `OURS` — and **refuses to pool captures of different origins**
(`require_single`, :238-259, raising `MixedCorpora`). It has **no build field whatsoever**.

The plumbing is unusually favourable in one direction and not the other:

- **Writers get it for free.** `origin.record(produced_by, origin, **extra)` (:98-106) already
  accepts arbitrary keys, and no writer today passes anything beyond `note=`:
  `wirecapture.py`:209, `livesession.py`:250/:362/:511 and `authsrv.py`:2846 pass `note=`;
  `test_tape.py`:56/:70 and `test_livesession.py`:361 pass no extra keyword at all. Adding
  `build=` is a keyword.
- **Readers need real work.** `origin_of()` (:152-223) neither parses nor returns a build, so
  every consumer changes: `tape.py`:183, `replay.py`:251, `behaviourrun.py`:351,
  `test_movement_fidelity.py`:135, and `origin.py`'s own CLI census (:262-280).
- **And the formats disagree.** The decrypted `game-*.jsonl` does **not** carry the build —
  `client_version()`'s own docstring says so at `tape.py`:525-528 — while `wire.jsonl` and
  authsrv's connection log do. A
  stamp that only some producers can populate needs `UNKNOWN` to be first-class, exactly as
  origin's third value is.

Follow origin's own best idea: **check the stamp against the file's own contents.** A stated
build contradicted by a recoverable one is REFUSED, not believed — the same move that caught
`dryrun_wire.jsonl`, a loopback capture stamped `live`.

Given opcodes demonstrably drift between builds, pooling two builds' captures is the same
class of error `origin.py` exists to prevent. **UNVERIFIED:** whether any existing corpus
figure already pools builds. Check the big ones first — the 22,524-message codec round trip
and the 155-opcode denominator over 12 connections — before assuming this is only a future
risk.

---

## 11. ~~The pre-update checklist — the highest-value deliverable here~~

✅ **LANDED 2026-08-13**, results in [FINDINGS.md](FINDINGS.md) §7.
`toolkit/updatecheck.py --before` / `--after`, wired into `RUNBOOK.md` as steps 0 and 0b at
the TOP of the update section, and into its failure table. Exit 0 / 1 changed-is-a-result /
2 could-not-run. `test_updatecheck.py`, 26 checks.

An update is not schedulable, half these measurements need the *before* state, and
`RUNBOOK.md`:136-139 already warns that snapshotting after accepting an update means the build
you were working against is gone. Right now the "before" work is prose in a runbook that a
session has to remember to read.

**Build one command that captures the whole before-state.** Contracts below are VERIFIED, and
two of them are worth knowing before you script them. `snapshot_client.py` and `dhbuild.py`
take **no arguments at all**; `snapshot_client.py` additionally hardcodes absolute paths
(`SRC`/`VAULT` at :21-22, bypassing `vaultpath`), while `dhbuild.py` resolves the vault
properly and hardcodes only the four subdirectory names:

| Step | Invocation | Exit codes |
|---|---|---|
| Client snapshot | `python toolkit/snapshot_client.py` (`SRC`/`VAULT` hardcoded, :21-22) | 0 every file verified byte-identical / 1 a file failed its hash / **3 something locked — incomplete** |
| DH accessor | `python toolkit/clientscan/dump_dh_params.py [exe]` | 0 `GO.` (generator 4, 512-bit prime) / 1 found but shape differs / **2 NOT FOUND — stop, the accessor moved and no patching tool can be trusted until it is re-derived** |
| Vault audit | `python toolkit/clientpatch/dhbuild.py` | 0 every build filed correctly / 1 at least one misfiled. Note: ours/stock/unknown is **printed**, not exit-coded |
| Archive baseline | `python toolkit/mapdata/datcheck.py --dat <archive> --snapshot before.json` | per §9 |
| Address baseline | the class-(a) census from §6, stored to diff against | — |
| Schema stamp | `schema/messages.json` → `validated_against_build` | — |
| Build id | §8's reader, once it exists | — |

Then **a second command that runs after**, diffs each, and prints one page: what moved, what
still resolves by signature, what needs re-deriving. Name its exit codes so an unattended run
is readable. Wire both into `RUNBOOK.md`:134 §"One-time setup, and again after every ArenaNet
update", at the top of the section rather than the end — and the failure table at
`RUNBOOK.md`:245 ("Anything at all after an ArenaNet update → redo the one-time setup in
full") should point at the command rather than at prose.

---

## 12. What "done" looks like

| # | Deliverable | Acceptance |
|---|---|---|
| 1 | ~~`msgshape.py` re-derived~~ | ✅ `db26a00`. 25 tables and 666 messages on both builds; a vacuous census exits 2; `test_msgshape.py` 37 checks, floor 37 |
| 2 | ~~`asserts.py` de-pinned~~ | ✅ `458b79d`. `single-routine=True`, no warning, both builds; `test_codescan.py` §10, floors re-measured to 93 / 45 |
| 3 | ~~`pinned.find()` fails closed~~ | ✅ `25cd1c4`. Refuses the live-install substitution; `BUILDS` is the one home; `test_pinned.py` 41 checks with a positive control on every refusal |
| 4 | ~~Class-(a) census~~ | ✅ `buildpins.py` + `test_buildpins.py` 40 checks; `FINDINGS.md` §2 carries the table with a verdict per row; 68 sites, 7 files, 37 outstanding |
| 5 | ~~Conversions landed~~ | ✅ `SIG_KEYS` has ONE implementation, not three that agree (`dhbuild.locate_keys`); the patcher and the go/no-go delegate to it; §7.2's two signatures are in `sigcorpus.py` and checked. `test_dhbuild` 43, `test_sigcorpus` 34 |
| 6 | ~~Build identity~~ | ✅ `buildid.py` + `test_buildid.py` 23 checks; the older build is **38519**; `pinned.BUILDS` is asserted against a fresh read of each image |
| 7 | ~~Build stamp on captures~~ | ✅ `origin.build_of` + `require_single_build`, contradiction-checked; `test_movement_fidelity` refuses to mix; `overrides.json` stamped; audit clean (1,122 files, all 38797); `test_origin.py` 28 checks |
| 8 | ~~Pre-update / post-update commands~~ | ✅ `updatecheck.py --before/--after`, exit 0/1/2 driven through the process, wired into `RUNBOOK.md` steps 0 and 0b and its failure table; `test_updatecheck.py` 26 checks |
| 9 | ~~Archive-durability experiment~~ | ✅ ARMED `studies/crossbuild/DURABILITY.md`; tracer in `vault/dat_durability/`, prediction stated before the event, revert proven on the real archive. Cannot be COMPLETED without an update |

**Filing.** This is maintenance, not a ladder rung — **do not invent an R-number**. When it
lands: `studies/crossbuild/FINDINGS.md` gets the results, `PLAN.md` §8 gets a line, `PLAN.md`
§6:803's risk row gets its "ongoing" replaced with the **measured** cost from deliverable 4,
`studies/review/FINDINGS.md`'s "26 message-table VAs" is corrected to 25 in **both** places it
appears (:581 and :205), its "30 addresses in `toolkit/`, 75 in `studies/`" gains a stated
counting method or is withdrawn, and any new test
gets its line in `CLAUDE.md`'s suite list **in the same commit** — `test_srclint.py` checks
that list against the tree in both directions and will go red otherwise.

---

## 13. Traps specific to this arc

- **A census in a stale tree.** §1. This is the one that would waste the whole session.
- **Two copies of 38797.** `vault/client/…` is pristine, `vault/run/…` is ours and differs in
  144 bytes including nine in `.text`. Route through `pinned.py` — and per §5, routing through
  it is currently weaker than it looks. A study of the shipped client that reads our own patch
  is reading us.
- **`C:\gw` auto-updates and is the owner's install.** Read-only, never patched, never
  launched. It is also the one copy that can change under you mid-session, and the one
  `pinned.find()` silently falls back to. If the measurement matters, take it from the vault.
- **A red test on a new build is a success.** Make the message say which build the expectation
  came from, or the next session debugs it as a bug for an hour.
- **`test_dhbuild.py`'s "both builds" is the wrong axis.** It means ours-DH versus stock-DH of
  the *same* build 38797, not two ArenaNet releases. `test_srctree.py` is the only genuine
  cross-build test in the tree; do not cite `test_dhbuild.py` as coverage this arc already has.
- **n=2.** Two builds, four months apart, both post-Reforged. Every stability claim in this
  arc inherits that limit and must state it.
- **Do not scrub the address citations.** Class (b) is permitted and the docs are built out of
  it — a location is a MEASUREMENT under `PLAN.md` §7 Q3, and the last session that read a
  provenance rule at maximum strictness rewrote 46 citations and reverted all 46. **Add build
  ids; do not remove addresses.**
- **Do not fix a number by re-deriving it a fourth way.** The 409/49 headline was withdrawn in
  §6 because it did not reproduce; the replacement is a *sourced* register, not a fresh grep.
  If a count in this document disagrees with the tree, correct it at the source and say which
  one moved.
