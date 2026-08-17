# U7 — the summit run: a retimed animation, rendered by the client

**Written 2026-08-17, when U6 landed.** This is the procedure for the ladder's
last rung. The run is **owner-driven by design** — the harness cannot aim a
camera or time a screenshot, and the behavioural rules put a human at the
keyboard for every client launch. Everything below the "Preparation" section
is for the operator; the preparation itself can be done by a session on your
go-ahead.

**What U7 proves if it goes green**: a unit animation we modified — pure
measurement-side integers, scaled through committed, review-gated code —
renders in the retail client from a rebuilt archive. That is round-trip
authorship, the goal the arc was scoped around.

## The modification

The named first case: **the burrowing worm (file 116366), sequence 2, key
times × 2** — the demonstration `test_skelwrite.py` already pins byte-for-byte
(the output differs from retail in exactly one int32 slot). Slowing one
sequence to half speed is visible to a person watching a worm burrow, and
measurable from a recording's frame timestamps.

## Preparation (a session does this, with your go-ahead)

1. Start from the **loopback** build's run directory (`vault/run/` — ours,
   caged, `updater=killed`; verify with `python toolkit/clientpatch/dhbuild.py`
   as always). Never the live one.
2. Copy `vault/run/Gw.dat` to a staging path under `vault/exports/unitwrite/`
   — the modification is made on a copy and swapped in, so backing out is a
   file rename.
3. Produce the modified container: `skelwrite.extract` → 
   `scale_sequence_keytimes(t, seq=2, num=2, den=1)` → `encode` →
   container re-emit (the test's §1 demonstration is exactly this, on the
   pinned anchor).
4. Write it into the staged archive via the datwrite path. **Known
   constraint** (the recorded wall): the modified container is the same size
   as retail's, but datwrite writes it *stored* while retail ships it
   *compressed* — the row will not fit its reservation and needs `datmove`,
   exactly as `test_skelwrite.py` §3 exhibits. Verify afterwards with the
   test's own checks: read-back identity, the nextStream chain, the three
   checksum rules.
5. Swap the staged archive into `vault/run/`, keeping the original beside it
   as `Gw.dat.retail`.

## The run (the operator — you)

Per `RUNBOOK.md`'s daily loop: cage verified, three terminals, the loopback
client at our server. Spawn the worm (definition 1442 — `npc.lakeside_worm`
in `content/npcs.toml`, served by the 0x0056 path; note it is 0x0056-only, so
no 0x0057 is needed).

**Watch for, in order:**

1. **Does the client load the map at all?** The two named risk candidates,
   in likelihood order: (a) it rejects the STORED row — no flags=515 row has
   ever shipped uncompressed to this client (21,420:1 compressed in retail);
   (b) something about the mid/tail companion rows beside the rewritten head.
   A crash dialog names its assert and line — **that name is the result**;
   write it down before dismissing. MdlLoad/MdlSeq/MdlAnim vocabulary means
   the FA1 side; Riff/stream vocabulary means the archive side.
2. **Does the worm render and animate?** If the client loads but the worm
   is missing or a default body, that is the 0x0056 path rejecting the
   definition — different failure, also worth its exact symptom.
3. **Is sequence 2 at half speed?** The measurement, not the eyeball: record
   a short clip (any screen recorder), and a session will extract the
   animation period from frame timestamps against the retail-archive control
   clip you record the same way after swapping `Gw.dat.retail` back.

**What to report back**: which of the three gates you reached, the assert
text verbatim if one fired, and the two clips if it played. Any of the three
outcomes advances the arc — a rejection names the next chunk family or the
compression question; a render at the wrong speed falsifies the key-time
reading; a render at half speed is the summit.

## Standing rules (unchanged, listed because this run touches the client)

Loopback only; the DH binding decides where a build may point
(`assert_launch_safe`); the cage stays verified; one client, human cadence;
nothing from this run leaves the vault.
