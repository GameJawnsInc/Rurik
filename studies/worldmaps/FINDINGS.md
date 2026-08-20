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

## WORLDMAPS-W2 — the first compression-8 MAP row a retail client reads. STAGED

The question no offline check can answer: does the client's re-bloat compiler
read a partner WE compressed? `gwenc`'s round-trip is through `gwdat`, OUR
decoder — "it proves agreement with our reader, NOT correctness against the
client's" (`datwrite.declaration_fault`'s own docstring). A8 answered this for
a generic row and A9 for a created chain; **no map's Stripped partner has ever
reached a client carrying bytes we compressed.**

The run sheet, predictions P1–P5 registered before anything is armed, exact
operator commands, and the fallback arm (`--stored-install`) are in
`vault/research/worldmaps/WORLDMAPS-W2-RUN.md`. Two arms on the C2 archive
copy: A = stored control, B = compressed treatment; the scorable claim is the
client compiles B identically to A (readback row-for-row, navmesh served on
the unarmed second run). Owner-driven.

## WORLDMAPS-W3 — an authored area under its OWN file id. OPEN

`datalloc --map` creates the two-row chain (armed head flags 259 + partner
flags 1) under a brand-new file id; the server names the geometry file id on
GAME_SMSG 0x0195 field 1 (OBSERVED 9/9 live connections,
`studies/maprows/FINDINGS.md`), so a created id is servable the moment
`content/maps.toml` names it. Plan: a deploy create branch through the
datalloc Python API (comp-8 partner via `Stream(..., extra_bytes=8, expect=)`),
`created = true` map rows, and an `[area.frontier]` row — ending the
displacement of row 71496.

## WORLDMAPS-W4 — the created chain meets the client. OPEN

Every "client compiles a map" result in the corpus reused a PRE-EXISTING file
id; `studies/customarea` FINDINGS 36 item 4 names the born-new case untested,
and `datalloc --map` has zero recorded uses against a client. The open
survival questions: does re-bloat fire for a head that was BORN zero-length
under a new id, does the compiled head land and survive Flush (A9's sweep
pattern), and does the partner stay untouched as it does for retail rows
(FINDINGS 35 + 39). Predictions will be registered in a RUN note before the
launch, with `rebloat.classify`'s UNCHANGED ambiguity disambiguated by the
Gw.log check from the start.
