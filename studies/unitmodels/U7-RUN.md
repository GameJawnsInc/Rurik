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

---

# THE RUN — 2026-08-17. U7 IS MET.

**A modification we authored renders in the retail client.** The hatcher's
skeleton, node bases scaled ×2 through `skelwrite`, drawn grotesquely
stretched by the pinned build-38797 client reading a `datmove`-rebuilt
archive. OBSERVED by the owner, screenshot with the run record. Not one
byte of that deformation is ArenaNet's: it is our decode → our typed
representation → our encode → our container → their renderer.

The chain, every link committed and review-gated: `skelfile` (U1) decoded
FA1 → `skelwrite.extract` (U6) → node bases ×2 → `skelwrite.encode` →
`rebuild_container` → `datmove` into a staged copy → the loopback client.

## It took four runs, and three of them were the experiment fighting itself

Recorded because the next session will otherwise pay the same tolls. None
of the first three failures was in the decode/encode chain.

1. **Wrong creature.** The plan's named case was the worm (116366). The
   harness's `--enemy` spawns the **hatcher** (definition 1471 = shell
   116228 + body 116703), and U4 had already proved those file sets are
   disjoint — so the client never read a modified byte. The operator was
   asked to eyeball an animation that could not have changed. *Read the
   assembly resolver's own answer before choosing a target.*

2. **A server bug that looked like ours.** Runs 1–2 died at
   `INSTANCE_LOAD_INFO` with `Code=007`, no assert, zero c2s — with AND
   without the modified archive, which is what exonerated it. Cause: the
   2026-08-14 crossbuild key fix lived inline in `handle()`'s **auth**
   branch and the **game** branch never got it, so a 38797 client was
   handed 38833's key and the ARC4 stream was noise. Fixed as one shared
   `bind_key_to_build()` with an AST regression check that both channels
   reach it (`test_handshake.py` section 0).

3. **Three things animating the target at once.** Run 3 used
   `--probe burrow`, whose step 4 deliberately re-creates the body at a
   **fresh agent id** (`_burrow_steps`' `FRESH_AGENT_ID` control step) — that is the second hatcher, and
   it is the probe doing its job in a test that had no business calling
   it. Add the combat arc making hostiles fight, and the creature was
   being driven by a burrow cycle, an AI and a probe while we tried to
   measure a model's playback rate. `--game-args="--practice-target"`
   (note the `=`: argparse only takes a `--`-leading value if it contains
   a space, which is why `'--probe burrow'` worked and
   `'--practice-target'` did not) gives one hostile standing still.

## What the run measured, beyond the summit

- **The shell's FA1 poses the creature.** The deformation lands from
  116228's own blk2C bases, so a COMPOSITED shell's skeleton is live in
  the renderer — not merely loaded. MEASURED.
- **Pose and playback rate come from different places.** Key times ×4 on
  the same file changed *nothing* visible (two clips, operator-reviewed),
  while bases ×2 on the same file changed everything. So the FA1 key
  table is not what sets idle playback speed — a real constraint on
  `studies/anim`'s timing reading, and the next question this arc leaves.
  (An earlier "superspeed" observation is NOT evidence either way: the
  burrow cycle and attack timing are server-driven and were animating the
  body themselves. It is recorded as uninterpretable, not as a result.)
- **A stored `flags=515` row is acceptable to the client** — risk
  candidate (a) above is REFUTED. The rewritten row is uncompressed where
  retail ships it compressed, and the client loaded, posed and animated it.
- **The animation library is currently unwritable, and that is the arc's
  standing wall.** The shell's first FA8 link (15018) carries 1.5 MB of
  FA1 — 237 sequences against the shell's sparse set — and `datmove`
  refuses it by name: *"nothing fits… the largest run datplan will hand
  over is 953,856 B"*. Retail ships it compressed; we write stored; no
  compression-8 encoder exists. Any authorship reaching the full animation
  set needs one, or an archive that may grow.
