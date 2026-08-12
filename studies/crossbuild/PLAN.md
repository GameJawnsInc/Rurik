# Cross-build resilience — what an ArenaNet update breaks, and what we do about it

**Handoff note, written 2026-08-12.** Nobody has owned this question. Pieces of the
answer are scattered across five documents and two of them contradict what the code
actually does. This arc's job is to turn "we know updates are a risk" into a list of
named files with a fix beside each one, plus one instrument that must exist *before* the
next update rather than after.

Results go to `studies/crossbuild/FINDINGS.md`. This file is the plan and gets struck
through as it lands.

---

## 0. Scope, and what this is not

**In scope:** what stops working when ArenaNet ships a new `Gw.exe` and `Gw.dat` —
static-analysis offsets, the patcher, the wire schema, the map layer, the two run
directories, and whether a capture taken on build A can be read against build B.

**Not in scope:** the WASM pivot. `PLAN.md` §6's hedge for this risk is "choose WASM:
the module bytes are the code and offsets come from the module", which is a strategic
re-platforming decision (§4, §7 Q1) and not something this arc gets to make in passing.
Assume the x86 client stays the target and cost the maintenance honestly; that number is
an *input* to the WASM decision, which is most of why it is worth measuring.

**Also not in scope:** making anything survive a build change that currently fails
*loudly*. A test that goes red on a new build is doing its job. The defect is a tool
that returns a confident wrong number, and §3 has a live example.

---

## 1. Before anything else, establish which tree you are in

```bash
git rev-parse --show-toplevel
```

This arc is a census. A census run in a stale worktree returns a confident number about
an old copy of the toolkit, which is the exact failure mode being investigated, one level
up. On 2026-08-11 a worktree was 33 commits and 42 `toolkit/` files behind `main` and
nothing errored.

Take a worktree under `.claude/worktrees/`, work in it, merge when the arc lands.
Pin every subagent to *that* path, require each command to begin `cd <tree> &&`, and have
each agent re-run the line above first and refuse on a wrong answer. For read-only
fan-out, `isolation: "worktree"` sidesteps the question. Recon fans out to Sonnet;
the classification calls in §4 stay on Opus/Fable.

---

## 2. What is already established — do not re-derive any of this

| Claim | Label | Where |
|---|---|---|
| The update happened *to us*: `Gw.exe` 10,404,032 → 10,483,904 B, `Gw.dat` replaced, DH struct RVA `0x6843e8` → `0x6910d8`, **both the prime and the server's public key changed** | MEASURED | `PLAN.md` §6:803 |
| ArenaNet rotates DH per build — Headquarter stores 107 server keys rather than one constant | UPSTREAM, corroborating | `PLAN.md` §6:803 |
| Six byte-shape signatures each reproduced their **exact hit count** (1/1/1/1 and 4/2) across a ~90-day build gap, while VAs drifted **non-uniformly**: 336 B mutex guard, 25,392–25,616 DH cluster, ~9,040 profession signatures, 320 assert callee. `.text` grew 44,032 B | MEASURED, n=2 | `studies/profession/WORKAROUNDS.md` §3.5 |
| **Any patch anchored to a raw address is broken by the next build; byte-shape anchoring survived both samples.** n=2 is induction, not a guarantee | MEASURED / stated limit | ibid. |
| In-place code ceiling is **78 bytes** — largest contiguous `int3` run in 5,471,232 B of `.text` (146,527 int3 bytes, 26,243 runs, 8 are ≥40, zero reach 100; the older build: 144,620 / 25,598 / 7 / 0 / **47**) | MEASURED, both builds | ibid. |
| Source-path census reproduces: 937 paths on 38797, 936 on `2026-04-30`; six spellings of "Server", zero hits, both builds | MEASURED | `test_srctree.py` §2–3 |
| The `CHAR_PROFESSIONS` census reproduces 29 sites / 13 files on both builds with relocated bases | MEASURED | `studies/profession/FINDINGS.md`:249 |
| `MOVE_TO_COORD` drifted `0x003C` → `0x003E` between builds — **opcodes are not stable across builds** | OBSERVED | `studies/movement/FINDINGS.md`:430 |
| A `Gw.dat` write survives a full play session unrepaired; the allocator relocates rows, but has only ever been observed doing it to the client's own scratch rows (8315/8316 moved, 8315 grew 92 → 96 B). Two sessions agree no text-band row, no skill icon and no content row was touched | MEASURED, n=2 | `studies/datwrite/FINDINGS.md` §6 |
| An MFT row index is meaningful only against the archive copy it was measured on; **file ids are the portable key** | design, enforced | `toolkit/mapdata/mapchunks.py`:117 |
| The two run directories diverge the moment a live session visits somewhere new, and it is invisible until something asks for the newer content: Ascalon City `map_file_id 113021` → row **177262** in `run-live/`, row **7982** in `run/`, and the loopback client asserted `Map.cpp(1762)` | OBSERVED 2026-08-10 | `RUNBOOK.md`:740 |

Three guards already exist and are the pattern the rest should follow:
`content.py` refuses a `source = "client-table"` row with no `build`;
`mapchunks.py` stamps its cache with the archive copy it was built from and **drops**
it rather than trusting it when the stamp disagrees; `pinned.py` names which `Gw.exe`
a tool read and why, because the vault holds two copies of 38797 that are **the same
length and differ in 144 bytes** — so a size guard cannot tell the pristine copy from
our patched one.

---

## 3. Fix first: the one cross-build breakage sitting in the tree

`toolkit/clientscan/asserts.py` carries `ASSERT_VA_38797 = 0x00487BC0` and uses it live
(`callee = self.base + (ASSERT_VA_38797 - 0x00400000)`). Against
`2026-04-30_b174de1f2d8d` it reports 19,680 sites with `single-routine=False` and its own
warning, because the callee VA belongs to the newer image
(`studies/srvtree/FINDINGS.md`:262 — "the older build's assert corpus is not currently
trustworthy, and that is worth fixing before anyone leans on it").

This is not cosmetic. `asserts.py` supplies the module ranges that `codescan.py --in`
narrows searches to, and §8/§9 of `test_codescan.py` exist because an under-counting
assert scan already produced two report rows that described no file in the image. An
under-count propagates silently into every search run inside it.

**Do:** locate the assert callee by byte shape rather than by VA — the routine every
assert site calls has a prologue, and the three call shapes (edx-first, ecx-first,
shared-tail) are all present on both builds, so the anchor exists on both. Keep the
pinned VA as a *cross-check* that prints when it disagrees, not as the lookup.

**Acceptance:** `asserts.py` returns `single-routine=True` with no warning on **both**
vaulted builds, and `test_srctree.py` / `test_codescan.py` stay green. Add the both-build
run to `test_codescan.py` as a section, with the shape counts as the assertion.

---

## 4. The census — and the trap inside it

A grep for eight-hex-digit constants finds **409 occurrences across 49 `toolkit/`
files**. That is an **upper bound and mostly noise**: this repo cites addresses in prose
constantly, and a citation is provenance, not a liability. Counting is not the
deliverable — classifying is. Three classes, and each gets a different verdict:

| Class | Example | Verdict |
|---|---|---|
| **(a) Live constant** the tool computes with | `ASSERT_VA_38797` at `asserts.py`:317 | Per-build liability. Convert to a signature (§5), or gate it behind a build check that refuses. |
| **(b) Citation in a comment or docstring** | `agents.py`:18, `genericvalue.py`:85 — where a finding came from | Harmless. Must carry its build id in the same breath; a bare VA with no build is the defect, not the VA. |
| **(c) Test expectation** | `test_skillcast.py`, `test_codescan.py` | **Wanted.** Going red on a new build is correct. The requirement is that the failure *says so* — "this address is from build 38797 and you are reading N" — rather than reading as an ordinary bug. |

**Use the syntax tree, not a grep.** A grep cannot tell a docstring from a constant, and
this repo has already been bitten twice by that exact substitution: `test_cmsgnames.py`
had a grep that asserted its own arm's formatting and reddened on a line break, and
`sweeploop.py`'s cage check hit the docstring explaining the rule. `test_srclint.py` and
`test_dispatch.py` both already walk `ast` and are the models.

**Deliverable:** a table in `FINDINGS.md`, one row per class-(a) site — file, symbol,
what it points at, whether a byte shape exists for it, and the cost of converting. That
table *is* the maintenance number the §6 risk row currently records as "ongoing", and it
is the input the WASM decision has been missing.

---

## 5. Conversion — signature anchoring, and the two rules that make it safe

The pattern is proven and already in the tree: `SIG_KEYS`, `SIG_MUTEX`, `SIG_DOWNLOAD`
and `KEY_TAP_CAVE_SIG` in `toolkit/clientpatch/dhbuild.py`, `TAP_SIG` in
`keytap_patch.py`, `SIG_KEYS` again in `dump_dh_params.py`.

Two rules, both already honoured by `keytap_patch.py` and both load-bearing:

1. **A signature must be unique in `.text`, and the tool must refuse on 0 *or* 2+
   hits** rather than taking the first. Taking the first hit is how a tool keeps
   returning a number after the thing it was looking for moved.
2. **Encode protocol constants and stolen prologues, not addresses** — the bytes that
   have a reason to stay put. `keytap_patch.py`:23 states this explicitly and is the
   reference.

**Free second sample:** §3.5 derived two signatures from scratch that are not in any
code — the attribute accessors (4 hits) and the `imul`-stride colour tables (2 hits).
Landing them costs little and doubles the corpus of shapes we have re-verified across
the gap.

**Do not report "signatures are stable".** It is n=2 induction over one build gap and
the study says so. The claim this arc can support is: *address anchoring failed on both
samples, shape anchoring survived both.*

---

## 6. `Gw.dat` across an update — the genuinely unmeasured half

What is known is §2's row: a write survives a *play session*. What a **content patch**
does to an authored row has never been measured, and the two open questions that depend
on it are both explicitly parked:

- Is a custom area durable or per-build? — `studies/customarea/FINDINGS.md`:756, :1229,
  :1952, asked three times and never answered.
- The **29 of 171,025 file ids carrying bit 31** are a stale/needs-refresh watchlist the
  client cleared on two entries in one session. `studies/datwrite/FINDINGS.md`:589 calls
  it "the single [most alarming] durability signal nobody has pulled on".

**The experiment cannot be run retroactively**, which is the reason this document exists
now rather than after the next update. It needs a *before* state:

1. Copy the archive to a scratch path (never `C:\gw`, never `vault/dat_study` — both are
   refused by the write guards, with positive controls that an ordinary copy is allowed).
2. Arm a known write with `datwrite.py` — journalled and reversible — and record the row,
   its reservation and its checksum.
3. Snapshot: `python toolkit/mapdata/datcheck.py --dat <copy> --snapshot before.json`
4. Let the update land on that copy.
5. `python toolkit/mapdata/datcheck.py --dat <copy> --diff before.json` and classify every
   change by FINDINGS 18.5's Tier 1 shapes — relocation, recycle, delete, sibling relink,
   or UNCLASSIFIED. Exit **1 means the archive changed and is a result**; exit 2 means it
   is too broken to have findings. Do not conflate them; that distinction cost a crash
   being reported as "the row moved".

**Predict first** (house rule): state, in writing, before step 4, whether you expect the
authored row to survive, be relocated, or be overwritten — and what each outcome implies
for the E3 / custom-area routes. A probe with no stated expectation can be rationalised
into agreeing with anything.

---

## 7. The pre-update checklist — the highest-value deliverable here

An update is not schedulable, half these measurements need the *before* state, and
`RUNBOOK.md`:136 already warns that snapshotting after accepting an update means the
build you were working against is gone. Right now the "before" work is prose in a runbook
that a session has to remember to read.

**Build one command that captures the whole before-state**, and put it at the top of the
runbook section:

- `snapshot_client.py` (exit 0 = every file verified; exit 3 = something locked)
- `dump_dh_params.py` — expect generator 4, a 512-bit prime, and `GO.`; **NOT FOUND means
  stop**, the accessor signature changed, and no patching tool in this repo or anyone
  else's can be trusted until it is re-derived
- `dhbuild.py` over the whole vault — which build carries whose DH, and the patch state
- `datcheck.py --snapshot` for each archive that matters
- the class-(a) census from §4, stored as the baseline to diff against
- the schema's build stamp (`schema/messages.json` → `validated_against_build`)

Then a second command that runs *after*, diffs each of those, and prints one page:
what moved, what still resolves by signature, what needs re-deriving. Name the exit codes
so an unattended run is readable.

---

## 8. Schema and captures — good shape, one real gap

**The schema story is mostly built already; do not re-invent it.**
`schema/messages.json` carries `validated_against_build: 38797`, `overrides.json`
records which arbitrated it, and `toolkit/schema/test_catalog.py` checks our catalog
against the client's *own* format tables — 477/477 GAME_SMSG field-for-field. That test
**is** the re-validation instrument: on a new build, point it at the new exe, diff, and
stamp a **new** schema revision rather than editing in place. The `0x003C` → `0x003E`
precedent is why in-place editing is wrong — an unstamped catalog is not stale, it is
actively dangerous.

**The gap is captures.** `toolkit/origin.py` stamps *whose server* produced a capture
(ours / live / unknown, three-valued) and **refuses to pool captures of different
origins**. There is no equivalent for build: `origin.py` has no build field. The build
is *recoverable* — `authsrv.py`:3140 records a `version` event carrying it, and it also
rides in the clear in the live `User-Agent: Gw/38797.0 (Win32)` — but it is not stamped
at the top and nothing refuses to pool across it.

Given that opcodes demonstrably drift between builds, pooling two builds' captures is
the same class of error `origin.py` exists to prevent. **UNVERIFIED:** whether any
existing corpus figure in the studies already pools builds. Check the big ones — the
22,524-message codec round trip, the 155-opcode denominator over 12 connections — before
assuming it is only a future risk.

---

## 9. What "done" looks like

| # | Deliverable | Acceptance |
|---|---|---|
| 1 | `asserts.py` de-pinned | `single-routine=True`, no warning, on both vaulted builds; both-build section added to `test_codescan.py` |
| 2 | Class-(a) census | A table in `FINDINGS.md`, one row per live constant, with a converted/gated/accepted verdict on each |
| 3 | Conversions landed | Each converted site refuses on 0 or 2+ hits; the two §3.5 signatures exist in code |
| 4 | Build stamp on captures | `origin.py` carries a build field; a pooling consumer refuses to mix builds; existing corpus figures audited for contamination |
| 5 | Pre-update / post-update commands | One command each, exit codes named, wired into `RUNBOOK.md` §"One-time setup" |
| 6 | Archive-durability experiment | Armed and documented with its prediction stated **before** the next update lands |

**Filing.** This is maintenance, not a ladder rung — do not invent an R-number. When it
lands: `studies/crossbuild/FINDINGS.md` gets the results, `PLAN.md` §8 gets a line,
`PLAN.md` §6's risk row gets its "ongoing" replaced with the **measured** cost from
deliverable 2, and any new test gets its line in `CLAUDE.md`'s suite list **in the same
commit** — `test_srclint.py` now checks that list against the tree in both directions and
will go red otherwise.

---

## 10. Traps specific to this arc

- **A census in a stale tree.** §1. This is the one that would waste the whole session.
- **Two copies of 38797.** `vault/client/…` is pristine, `vault/run/…` is ours and
  differs in 144 bytes including nine in `.text`. Route through `pinned.py`; a study of
  the shipped client that reads our own patch is reading us.
- **`C:\gw` auto-updates and is the owner's install.** Read-only, never patched, never
  launched. It is also the one copy that can change under you mid-session — if the
  measurement matters, take it from the vault.
- **A red test on a new build is a success.** Make the message say which build the
  expectation came from, or the next session debugs it as a bug for an hour.
- **n=2.** Two builds, four months apart, both post-Reforged. Every stability claim in
  this arc inherits that limit and must state it.
- **Do not scrub the address citations.** Class (b) is permitted and the docs are built
  out of it — a location is a MEASUREMENT under `PLAN.md` §7 Q3, and the last session
  that read a provenance rule at maximum strictness rewrote 46 citations and reverted all
  46. Add build ids; do not remove addresses.
