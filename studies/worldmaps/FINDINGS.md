# World maps — authored areas that coexist

The arc: retire the two constraints that keep authored areas one-at-a-time and
small — the uncompressed install (every authored map had to be SMALLER than
what ArenaNet compressed into its row) and the displacement mechanism (every
authored area overwrites a live retail map's rows, currently 71496/71497 via
map 143). Four rungs; the even ones are owner-driven client launches with
predictions registered first, A9/A10 style.

**Identifiers.** `WORLDMAPS-W<n>` = rungs of this arc's ladder, defined in this
document. Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md);
never bare `W1`–`W4`, which collide with `studies/profession` among others.

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
