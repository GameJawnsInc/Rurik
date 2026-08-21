# World maps — authored areas that coexist

The arc: retire the two constraints that keep authored areas one-at-a-time and
small — the uncompressed install (every authored map had to be SMALLER than
what ArenaNet compressed into its row) and the displacement mechanism (every
authored area overwrites a live retail map's rows, currently 71496/71497 via
map 143). W1-W4 did that and are landed, the even ones client-proven; W5-W7
carry it forward into the authoring LOOP (headroom, scale, and a walked
region). Client launches are staged A9/A10 style with predictions registered
first.

**Identifiers.** `WORLDMAPS-W<n>` = rungs of this arc's ladder, defined in this
document. Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md);
never bare `W1`–`W7`, which collide with `studies/profession` among others.

Labels per [studies/character/FINDINGS.md](../character/FINDINGS.md).

## WORLDMAPS-W1 — deploy installs compressed. LANDED 2026-08-20

**OBSERVED (offline; the client witness is WORLDMAPS-W2's question).**
`deploy.py --install` now compresses the assembled Stripped partner with
`gwenc.encode` and judges replace-vs-relocate on the COMPRESSED size, threading
`--compression 8 --expect <plain blob>` through BOTH writers (`datwrite
--replace` and `datmove --move`) so the deviation cannot reappear on the
relocate arm. `--stored-install` preserves the old behavior byte-for-byte as
the control arm. The readback now asserts what a READER gets back (Archive.read
decompresses), plus a second refusal that the row is MARKED with the code we
asked for — "the payload is right" and "the row is marked the way retail marks
it" are two claims.

**Measured gain, two corpora — do not mix them when quoting.** Against build
38797's real donors (`install_bytes`' docstring, the CLI's own print):
32×32 3,941→1,316 B (33.4%), 64×64 10,654→2,012 B (18.9%), 96×96
21,786→2,828 B (13.0%) — so against map 143's shipped 4,608 B partner
reservation, **96×96 replaces in place where 32×32 was previously the largest
map this toolkit could install at all**. `test_deploy.py` §4's fixtures (no
donor constants) measure 20.2% / 12.7% / 9.7% on the same dims; the test
bounds the claim only as "strictly smaller", never a pinned number.

Retail's own Stripped partners are compression-8; ours were the deviation
(readable in FINDINGS 35–58 of `studies/customarea`, but the deviation). W1
restores the retail shape. `test_deploy.py` floor 35→56 (§7: five real
installs against a hand-laid archive whose reservation the FILE chooses; §5's
AST pins moved with the dispatch and got stronger). Skeptic verdict clean,
zero must-fix; the ten notes are recorded in the arc's workflow output and the
two that were doc-level (RUNBOOK's stale live-constraint sentence, the RUN
note's log-naming ambiguity) were fixed at integration.

**Known consequence, deliberately unwired:** a compressed install SHRINKS the
row (map 143's partner 4,608→1,536 B after a plaza), so iterating small→large
relocates where it used to sit still. `datwrite --replace grow_to=` is exactly
the flag for it and is its own change with its own gate; folding it into W1
would have made a failed install ambiguous between two mechanisms.

## WORLDMAPS-W2 — the first compression-8 MAP row a retail client reads. RAN GREEN 2026-08-20

**OBSERVED (retail client, build 38797, one map, one launch per arm —
agent-driven on the owner's explicit go-ahead; the readouts are mechanical, so
the owner-drives boundary did not bite).** Two arms on the C2 copy, control
first, one flag apart. **The client's re-bloat compiler READ the partner we
compressed and built the identical map**: arm B's readback matches arm A line
for line and both reproduce FINDINGS 56 (6,627 B path chunk, 55 trapezoids,
1024/1024 heights, env/sound verbatim, 5/5 props, spawn in one trapezoid);
the server's own navmesh line named the same 55 on the unarmed second run,
both arms. The partner was never touched by the client — after arm B's
session, still 0x81B5000, still 1,316 B (33.4% of stored), still compression
8 — and the head came back REBUILT at ArenaNet's own trapezoid count.
Post-flight: the diff names exactly the two expected rows, `--assert-safe`
clears everything. Full scoring of P1–P7, artifacts, and two honest caveats
(the sheet's Gw.log capture is clobbered by the serve run's second client;
the serve check's population half hit the server's benign no-rows line in
both arms, orthogonal to compression — since closed on main, `ec5f426`:
`serve_run` gained a third verdict SERVED-UNPOPULATED, and the suspected
content drift did not happen, plaza never had a spawn row and FINDINGS 56's
"5 of 5" is its PROPS readback) are in
`vault/research/worldmaps/WORLDMAPS-W2-RUN.md` §RESULTS.

**What this closes**: the last place an authored map deviated from retail's
own shape, and the in-place size cap — 32×32 before, at least 96×96 measured
now. Scope travels with the witness: one map, one shape, one build.

## WORLDMAPS-W3 — an authored area under its OWN file id. LANDED 2026-08-20

**OBSERVED (offline; the client witness is WORLDMAPS-W4's question).**
`deploy.py --install` now ALLOCATES the map chain when the area's maps.toml
row carries `created = true` and its file id binds nothing in the target
archive: `create_streams` builds `[Stream(b"", 259), Stream(gwenc_stream, 1,
extra_bytes=8, expect=plain)]` and `create_chain` drives
`datalloc.plan_alloc`/`alloc`, journaled, spilling the compression-8 stream
BEFORE the plan (a refused allocation still leaves behind the thing that was
refused). The head is born armed — zero length, the re-bloat trigger — and is
not armed again. A bound id falls through to the normal install (idempotent);
a non-map-chain shape, a taken id, or a bit-31 sibling each refuse by name
(the sibling refusal is the CALLER's because `plan_alloc`'s exact-membership
gap — archivewrite §17.5 — is still open). `create_note()` answers on EVERY
run, including build-only dry runs, so "the create branch would fire" is
previewable without a write.

**The content rows, and one ruling.** `content/maps.toml [map.166]`
(created = true, file id 0x5F0B0, source="invented") and
`content/areas.toml [area.frontier]` (64×64, donors by file id per the sculpt
pattern). The spec said the area "may keep map_id 143" — **not implementable**:
deploy joins area→map row BY map_id, so pointing at 143 resolves the
displacement row and the create branch could never fire. Ratified: the area
points at its own [map.166]; the map id remains a cosmetic label exactly as
[map.143]/[map.144] describe theirs. P1 (the full allocation plan against the
C2 copy, read-only) was independently re-measured and reproduces byte for
byte, row indices and MFT arithmetic included.

**A created row is a THIRD content state, and it nearly deleted a guard**:
`contentids.check` returned FATAL for the unbound created id, which — under
`served=None`, the fail-closed default — would have refused every loopback
launch in the repo. It now records an absent created id as a printed SKIP and
judges it normally the moment an archive binds it; `test_contentids` holds
created rows out of both archive-selecting scans. Floors: test_deploy 56→92,
test_content 39→40, test_contentids 19→20.

**Residuals recorded, none blocking** (skeptic notes, fix pass took the two
must-fixes): the born-armed clause has no check behind it; `created = true`
beside an id that binds a RETAIL map chain silently returns to displacement
(the install fall-through is also the displacement path — a row comment names
it); the create path overwrites an existing `<area>_alloc.json`; contentids'
created-skip fires before the server side is consulted; two of `map_chain`'s
four shape refusals are hand-verified but unexercised by the suite.

## WORLDMAPS-W4 — the created chain meets the client. RAN GREEN 2026-08-20

**OBSERVED (retail client, build 38797, one map, one launch cycle —
agent-driven on the owner's go-ahead, mechanical readouts).** The client
resolved a map chain born under file id 0x5F0B0 — an id nothing had ever
bound — logged FINDINGS 35's exact re-bloat line naming it
(`'0x05f0b0' failed to load.  Attempting to re-bloat.`), compiled our
terrain from the 2,028 B compression-8 partner, wrote the head back REBUILT
(0 -> 6,012 B comp 8, relocated, 64 trapezoids over 1 plane), left the
partner byte-untouched across three sessions, and kept the registration
through its own Flush — the diff names only our two created rows plus the
client's scratch rows 8315/8316, nothing UNCLASSIFIED. Readback 6/6 including
the spawn-in-one-trapezoid check [map.166] recorded as owed; the server's own
navmesh line named the same 64. All ten predictions scored in
`vault/research/worldmaps/WORLDMAPS-W4-RUN.md` §RESULTS, which also records
the run's two lessons: a fresh run directory needs its own firewall CAGE (the
first launch was refused fail-closed — the cage is per-path; owner ran
isolate_client.ps1 and the re-run proceeded), and the launch stages were
split to keep the compile run's Gw.log from the serve sessions (W2's capture
defect, fixed procedurally). The throwaway was delta-captured (PROVEN,
`vault/deltas/worldmaps-w4`, 24,736 B) and deleted — datdelta's first real
customer.

**What this closes**: FINDINGS 36 item 4 (the born-armed, never-bound case);
A9's witness extends from "a created chain is READ" to "a created chain is
COMPILED"; and displacement is retired — the next authored area does not
have to take rows 71496/71497 hostage. Still unestablished, per the sheet:
survival across a client patch, more than one created map per archive (the
C2-lineage MFT slack is exactly one chain), a second created chain in one
session.

## WORLDMAPS-W5 — headroom: an area declares its own budget. LANDED 2026-08-20

**OBSERVED (offline, this tree).** The gap W1 recorded and W4 inherited: a
compressed install SHRINKS the row, and a created partner is sized to its exact
payload — `datalloc.Stream` has no reservation parameter and `_place` computes
`blocks_for(len(data))` — so the *second, larger* install of any area, created or
displaced, relocated. `datwrite.replace(grow_to=)` was the flag for it and had
exactly one caller (`restore()`), because `grow_to` needs a "what this row was
GIVEN" number and **a row's true reservation is recorded nowhere**
(`datwrite.py:875-880`: "the bound therefore has to come from GEOMETRY").

**The answer is that the AREA states it.** `content/areas.toml` rows carry an
optional `reserve_bytes` — an authoring budget with provenance, not an inference
— `datalloc.Stream(reserve=)` honours it in placement block-sizing ONLY (size,
crc, `expect` and every existing gate stay bound to the real payload), and
`deploy.install_partner` spends it: a stream past the row's current reservation
but inside the declared budget now GROWS BACK IN PLACE instead of relocating.
Measured: a created chain given a 2,048 B budget takes a 1,952 B second install
at the same offset, where the same install with no budget relocates. Before this
rung that arm did not exist.

**Two things the skeptic corrected, and both are the interesting half:**

1. **The grow arm is scoped to a row WE created.** The first build gated only on
   the budget, so an area declaring `reserve_bytes` beside a DISPLACED retail row
   would have grown ArenaNet's row into blocks it never gave us. Now
   `install_partner(..., created=)` requires both, the preview mirrors the same
   gate so it cannot promise a verb the install will not pick, and the relocate
   line says why: *"this row was not created by us, so what it was given is
   ArenaNet's statement and not ours."* The control is one field apart and takes
   the opposite verb.
2. **A check that asserted only "it raised, and nothing was written" could not
   fail for its own reason.** `datmove` independently refuses the same lie and
   re-raises the same sentence with the archive byte-identical, so a fallback
   recogniser that misclassified a declaration fault as a claimant conflict
   stayed invisible — MEASURED by breaking it: the run printed "THE GROW GATE
   REFUSED: <a temp-file path>" and relocated around a bad declaration while the
   suite stayed green. The check that catches it is the NEGATIVE on what the run
   SAID it was doing.

Also fixed at the root: a raw `datalloc.Refused` escaped `create_chain` past
deploy's own handler (exit 1 with a stack instead of exit 2 with a remedy), and
`int(area.get("reserve_bytes", 0) or 0)` silently truncated `2048.5` and let
`-512` through — `area_reserve()` now refuses a non-int, a bool and a negative,
naming the file to edit. Floors: `test_deploy` 112→167, `test_datalloc`
177→203. Four sabotages driven by hand, each red on the guard it names.

**Still open, deliberately:** `grow_gate_refusal` joins on datwrite's MESSAGE
TEXT (four markers) and fails SAFE if datwrite rewords — a typed refusal out of
`_grow_gate` is the strong fix and belongs with the residuals pass, since it
touches datwrite, which this rung was told not to.

## WORLDMAPS-W6 — the scale ladder, measured. LANDED 2026-08-20

**OBSERVED (offline, real runs against `vault/run/2026-07-29_221c13772c7a-c2`,
generator `plaza`, donors by file id 0x1B97D→row 7982 and 0x22E2C→row 46196).**
`toolkit/mapdata/mapscale.py` walks a ladder of dims through deploy's own
pipeline and reports what each costs, because the corpus stopped at 96×96 and
`install_bytes`' docstring explicitly refuses to extrapolate its three points:

| dim | cells | authored | comp-8 | % stored | blocks |
|---|---|---|---|---|---|
| 32×32 | 1,024 | 3,822 B | 1,256 B | 32.9% | 3 |
| 64×64 | 4,096 | 10,535 B | 1,956 B | 18.6% | 4 |
| 96×96 | 9,216 | 21,667 B | 2,768 B | 12.8% | 6 |
| 128×128 | 16,384 | 37,026 B | 3,572 B | 9.6% | 7 |
| 192×192 | 36,864 | 80,916 B | 4,232 B | 5.2% | 9 |
| 256×256 | 65,536 | 142,195 B | 4,820 B | 3.4% | 10 |

All six round-trip **100% of samples exactly**; assemble+compress at 256×256 is
0.28 s. **Authored maps compress BETTER the bigger they get** — 64× the cells
costs 37× the stored bytes and only 3.8× the compressed stream, because only
terrain tag 1 is entropy-coded and everything a generator emits around it is
repetitive raw bytes.

**The result that matters is which budget binds: not bytes, ROWS.** A 256×256
partner is ten blocks against a largest usable run of 953,856 B on that copy —
the byte budget is not close to binding at any dim on this ladder. MFT slack is:
the 38797/c2 line has 48 B = 2 rows = exactly **one** more created map; the
38833 copy has 424 B = 17 rows = **eight**. Any multi-area work belongs on the
38833 line; single-region work can stay on the proven 38797 one.

Two guards the skeptic added are worth naming because they are the same defect
class this repo keeps meeting: a `Capacity` restored from a JSON report
manufactured a FALSE placement answer ("no usable run is big enough" for a
stream its own summary said fits by 197×) and now refuses as un-measured, and
`Rung.from_dict` accepted MISSING fields so an empty record claimed a perfect
round trip (`None == None`). Floor 62 (66 under `--big`), 1 declared skip.

**Open, and NOT chosen between two readings:** `dat_study_38833`'s largest
usable run measures 2,892,800 B — *unchanged* after the 2026-08-17
extent-projection fix that `studies/archivewrite` §1.5 says should have withheld
it. Either the fix does not reach that run (a live gap) or §1.5's diagnosis
needs amending. Re-measured read-only 2026-08-20; recorded, not resolved.
