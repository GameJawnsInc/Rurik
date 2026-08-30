# Movement — the arc handoff, and the entry point for all of it

**Rewritten 2026-08-30 at `201324c`, tree clean, branch `main`.** The header this
replaces was written 2026-08-19 and last touched 2026-08-20; ten days and roughly
forty commits of movement work landed after it, on a channel it does not mention.
**Everything from §0 down is that older record**, kept because its mechanism decode is
still the best statement of the warp and is still largely true — read it with §A's
staleness table beside you.

Status authority remains `PLAN.md` §3; the live next-actions list is `PLAN.md` §8. How
far to trust any number here: [studies/method/FINDINGS.md](../method/FINDINGS.md).

> ## ★ FOUR THINGS A COLD SESSION GETS WRONG HERE, ALL OF THEM OBSERVED
>
> **1. There is no single entry point, there is a CYCLE — and this file is now the
> top of it.** `HANDOFF-WARP.md` sends you to FINDINGS §1p.10; `HANDOFF-PLANE.md`
> sends you to `PLAN.md` §8 and §3; §3's R3 row (unedited since `2d784d9`,
> 2026-08-20) sends you *here*; and this file, until today, said nothing about the
> plane channel at all — it does not contain the string "movecode". Two more files
> each declare themselves an entry point (`studies/movecode/PLAN.md`,
> `studies/movement/RETHINK.md`). Read §A before opening anything else.
>
> **2. The plane repair is ON BY DEFAULT, it has NEVER FIRED, and its only live
> arming was probably a FALSE FIRE.** Measured 2026-08-30 and written down nowhere
> before this: all three of R7's `arming` rows sit on the west bridge, where our
> mesh offers **only the deck**. See ★3 — this is the arc's most important open
> problem and it is a design property, not a bug.
>
> **3. The repair's safety test is INVERTED — it is most confident exactly where
> our decode is worst.** It arms only when `plane_at` returns ONE unambiguous
> candidate. Where our decode HOLDS a stacked deck it returns two planes and
> DISARMS; where our decode MISSES the ground under a deck it returns one and ARMS.
> Measured over both bridges on map 280 (fine scan at 8 u, `containing()` per
> sample):
>
> | deck | our decode | offers ONE plane → **arms** | offers 2+ → disarms |
> |---|---|---|---|
> | west bridge, plane 37 | misses the under-deck ground | **4,671 / 4,723 = 98.9 %** | 52 = 1.1 % |
> | NE bridge, plane 42 | holds the `{0,42}` stack (§1z-g.5) | 3,572 / 6,821 = 52.4 % | 3,249 = 47.6 % |
>
> R7's client declared plane **0** at each arming point while our mesh offered only
> **37**; had the streak reached `PLANE_REPAIR_HOLD` the repair would have restamped
> the player onto the bridge above them. It never got past 1.02 s of 5.0 s. This is
> the false-fire class the doctrine block prices as "no measured instance in four
> sessions" — there is now a candidate instance, and §D is what to do about it.
>
> **4. DO NOT make the server rewrite outbound grant planes.** "Never emit a plane
> the mesh does not offer at the emitted point" is the obvious fix, it is wrong, and
> it is refused repeatedly in `authsrv.py`'s own comment blocks — `plane_at`'s
> 9-of-198 failure class is exactly *"the client's plane is CORRECT and our decode's
> coverage is missing"*, one such send site was already reverted for overruling the
> client in precisely the wrong place, and `test_position_trust` pins verbatim echo
> at the zero-lead site **as design**. An instantaneous geometry test cannot tell a
> deck we failed to decode from a stale plane. ★3 is the same fact from the other
> side. Grep the graveyard before proposing anything:
> `grep -n "REFUTED\|reverted\|do not re-propose" toolkit/authsrv/authsrv.py`.

---

## A. Which document, and how stale — read this table before opening one

| Document | What it is for | Currency |
|---|---|---|
| **this file** | the arc's entry point; where each thread stands and what to do next | current at `201324c` |
| `studies/movecode/FINDINGS.md` | **the record.** Newest sections supersede everything above them | current; §1z-m is the newest |
| `studies/movecode/HANDOFF-PLANE.md` | deep-dive on the plane channel and the lock | **stops at §1z-i**; misses `1ce0171`, `30055e0`, `d710a67`, `131c84a`, and its own "written at `dcf9484`" stamp is wrong (last edited `2882627`) |
| `studies/movecode/HANDOFF-WARP.md` | deep-dive on the warp hunt and the candidate graveyard | lists `--router` REFUTED in two tables; §1y/§1z/§2a reversed that and every runsheet since passes it |
| `studies/movement/CANCELWALK.md`, `REALFIX.md`, `ROUTER.md` | the shipped policy arms and their runs | see §C; several carry self-status headers that are wrong (§G) |
| `studies/movement/PROBE-GATEFIRE.md` | the gate-fire operator procedure | §6 is pinned by `test_probedoc.py`; its prose is not — its "n = 0 captures" claim was corrected 2026-08-29 |
| `studies/movecode/RUN-*.md` | per-run runsheets | **there is no `RUN-R7.md`** — the arc's most decisive run has no runsheet, and its scoring scripts are one-off files under `vault/research/movecode/r7/scoring/` |

**The rule this table exists to enforce:** a document that asserts its own status lies
within days. Four do it today — `RUN-B2.md` "nothing is armed", `RUN-R2.md` "UNRUN",
`REALFIX.md` "NOTHING HERE HAS BEEN RUN AT A CLIENT", `studies/movecode/PLAN.md`'s B2
site priority prescribing a site `movehook.c` refuses under owner ruling Q12(d). Where
you must state status, state the **test**: *"this ran iff FINDINGS has a §1t heading —
`grep -n '^### 1t' studies/movecode/FINDINGS.md`."*

## B. Where each thread stands

**The plane channel — the newest thread and the best-measured.** `m_point` is
`float x, float y, int plane, int`, and the plane is a second channel the arc scored
nothing on for two weeks. **A plane desync is a LOCK where a position desync is only a
warp**: R7's return tap measured the client's own pathfinder returning `pathCount == 0`
**exactly** when its declared from-plane is one the mesh does not offer — exceptionless
over 214 live queries in both directions, with a natural experiment (two queries 1.2 s
apart, bit-identical from-point x/y dwords, differing only in the plane word, answered 1
and 0). A client that cannot resolve its own position cannot walk to ground that would
re-plane it. Three locks exist in the corpus, all before the shipped default. The repair
ships ON; it has never fired; the heal is **untried**, supported only by §1z-g.3's
accident, where a routed grant's plane word revived a dead walker in 81 ms.

**The warp / no-clip thread.** The mesh HAS the mountains — prop placements carry
authored outline rings and the retail mesh carves them (97 of 98 ring interiors fully
unwalkable on map 280; the rock the operator no-clipped through is carved edge-for-edge).
The four earlier detectors died on 8.9–19.8 s event-sampling gaps sitting exactly over
the repro windows, not on mesh content — **score chords and outline membership, never
point samples.** The client's walker consults its pathing query every ~16 ms and
**ignores the answer**: the result gates only the `+0x68` copy, while movement
dead-reckons from `+0x78`. **Wall integrity on retail was always the server's grants.**

**The shipped policy arms.** Five movement arms are ON by default, each by an owner
ruling; `--router` and `--click-echo` are NOT (§C). The candidate graveyard is real and
the tree currently states its size four different ways — do not quote a count, read the
flags.

## C. What is actually running — and how to find out without guessing

**Do not grep the module globals.** They read `False` while `main()`'s argparse arms
five of them, and `HANDOFF-PLANE.md`'s Terminal-1 command is only half right (it passes
`--router`, which is `store_true` and **off** by default — so no live trial of the plane
repair has ever run the shipped click policy).

**The server's own startup banner is the authority.** It prints the resolved policy
including the note that three separate senders can emit `0x002C`. Start it and read it.
That is a statement that cannot go stale, because it names an artifact that regenerates.

ON by default: `--zero-lead`, `--plane-carry`, `--grant-suppress`, `--cast-stop=pin`,
plane repair. Each has a `--no-` revert. OFF: `--router`, `--click-echo`.
**`--grant-suppress` and the heading arm share ONE rate-limit clock**, so between them
they cannot exceed one grant per 0.50 s — say which flags were on when you report a run.

**The plane repair has no owner ruling on record.** Q9–Q12 all have one; this does not.
It puts a `0x002C` on the wire by default on the authority of a code comment. Given ★3,
that is worth raising.

## D. The next action, and why this one

**Run the plane-disagreement census over the corpus that already exists.** For every
accepted `position_report` carrying a declared plane, compare it against what our decoded
mesh offers at the reported `(x, y)`; break the disagreements down by map, by geometry
class (stacked deck / bridge underwalk / open ground), and by whether the declared plane
is `0` or non-zero.

Desk-only. No client, no owner, no new instrument, blocked on nothing. The join already
exists in `pathdiff.py` pointed the other way (it uses plane agreement to *identify* a
mesh; this uses a known mesh to *census* agreement).

It settles, in order of value:

1. **The false-fire base rate — the repair's licence.** The doctrine block defaults the
   repair ON arguing the false-fire class "has no measured instance in four sessions".
   Four sessions is not a measurement, and ★3 says the one arming we have is probably an
   instance. This turns "we have not seen one" into a rate, per geometry class.
2. **What a declared plane of `0` means** — and it is load-bearing both ways.
   `pathdiff.py` explicitly refuses to reason from a declared 0 (its plane-agreement
   discriminator is restricted to non-zero, because plain agreement reads 59–67 % on
   *wrong* meshes), while the repair's trigger draws its strongest inference from exactly
   that value: every R7 arming is "client declared 0". One instrument refuses to reason
   from plane 0; the other acts on it. Nobody has established whether 0 is a valid index,
   a null sentinel, or both depending on map.
3. **The 9-of-198 `plane_at` failure class**, the load-bearing counterweight in every
   refusal of the "never emit an impossible plane" fix. It has never been counted at
   corpus scale.
4. **A denominator for the `plane_echo` tripwire**, which currently has none.

**Why not "score R7's server-side readout" first**, which is the obvious pick (its 9
ladder rows and 9 echo rows are unpublished, and it reached `holding` twice — the
furthest the shipped repair has ever advanced): because per ★3 that write-up should not
be attempted before the census, or the arming gets published as encouraging when it is a
near-miss on a false fire.

**Why not a live run for the heal:** highest value if it works, but a lock is not
provokable — zero fires in three armed sessions, and two of the three known lock classes
are structurally invisible to the trigger (off-mesh disarms by design; and a *moving*
client carrying an impossible plane re-arms the clock on every report and can never
accumulate `HOLD`, which is precisely what R7 was). The census makes that run
better-designed when it happens, by naming which geometry to press against.

## E. Traps, from the record rather than from imagination

1. **★4's refused fix.** A cold session proposes it within ten minutes.
2. **`attach.py --stop` ENDS THE CAPTURE.** It is the last thing you do. On 2026-08-29 a
   run was stopped and then played on, and the most interesting thing the operator saw is
   not on the wire.
3. **Establish which tree you are in** — `git rev-parse --show-toplevel` — and pin
   subagents to *that* path with every command beginning `cd <tree> &&`. Naming a tree in
   prose does not move the shell.
4. **Never pick a client build by filename.** `sorted(exes)[-1]` has chosen wrong three
   times, and `vault/run/` now also contains `reskin-roster`, which sorts last and is not
   a build. Use the explicit path plus `python toolkit/clientpatch/dhbuild.py`.
5. **A relative `--exe` fails in an agent shell and this is NOT a `session.py` bug.**
   Agent shells export `NODEFAULTCURRENTDIRECTORYINEXEPATH=1`, which disables
   CreateProcess's current-directory search. The runsheets are correct at the owner's
   terminal. Use an absolute path and stop debugging.
6. **movehook's observer effect is unmeasured.** Nineteen persistent `int3` taps, four on
   `MapFindPath` returns and one at ~16 ms cadence. Every timing claim on this arc rides
   through them — the 81 ms heal, the 1.02 s streak, the 5.2 s transient. No test
   addresses it.
7. **Four instrument defects were found in one day (§1z-j…§1z-m).** They did *not* move
   the plane headline — `pathdiff` on r7 still reproduces AGREE 97 / DIFFER 34 /
   UNCOMPARED 13 / OFF-MESH 63 — but they did move older published numbers, **per figure
   and not as a blanket invalidation**: r4a's off-mesh depths moved materially (median
   239 → 228.2 u), while §1z-g.1's 20.2 u moved 0.5 %. Re-derive the specific figure you
   are about to lean on; do not assume it is either fine or void.
8. **`--map auto` picked the WRONG map before `1ce0171`** (an area term ranked another
   map above 280 on a map-280 capture, reporting OFF-MESH 3 instead of 63). Most
   published numbers do not record which mesh they were scored against.

## F. Commands

Terminal 1 — the server. **Note `--router` is not the shipped default**; pass it only if
you are reproducing R6/R6b/R7, and say so in the write-up:

```bash
python toolkit/harness/session.py --exe C:/gd/Rurik/vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 2400 --game-args="--router --map 280"
```

Terminal 2 — arm the client hook once you are in the map. Do **not** regenerate sites:

```bash
python toolkit/clientscan/movehook/attach.py --minutes 8 --out vault/research/movecode/r8
```

Last thing, after everything you want measured:

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

Score the plane channel (section C; orthogonal to A and B):

```bash
python toolkit/clientscan/noclipscore.py --bin vault/research/movecode/r8/movehook.bin
```

The affected-test set for this arc — each prints its own count and floor and exits
non-zero if short, so never quote a total:

```bash
python toolkit/authsrv/test_planerepair.py; python toolkit/authsrv/test_position_trust.py; python toolkit/authsrv/test_poschecksum.py; python toolkit/authsrv/test_cancelwalk.py; python toolkit/authsrv/test_router.py; python toolkit/authsrv/test_familyrate.py
```

Before touching the instrument:

```bash
python toolkit/clientscan/movehook/test_movehook.py
```

## G. How to read the numbers in this file

**They rot in hours, and this arc has the receipts.** `HANDOFF-PLANE.md` went stale
**76 minutes** after it was written: its opening paragraph says section C finds 6
anomalies in `r5bridge`, and the same afternoon's commit moved it to 8.

So: corpus counts here are **floors with a signature set**, never values. The repair's
fire count is the one that matters — expect **0**, and expect at least three sessions
carrying `plane_repair_due` rows with the signature set `{132441, 142904, 163930}`:

```bash
python -c "import glob,json;n=0;s=set();[ (n:=n+1) if r.get('kind')=='plane_repair' else s.add(f[-22:-16]) for f in glob.glob('vault/captures/gamesrv/*.jsonl') for r in (json.loads(l) for l in open(f,encoding='utf-8',errors='replace') if l.strip()) if r.get('kind') in ('plane_repair','plane_repair_due')];print('fires',n,'| sessions with a ladder',sorted(s))"
```

**A non-zero fire count is the arc's headline result, not a stale number.** State the
glob you used — flat gives a different total from recursive, and both have been
published.

Anchor on grep-able strings, never on line numbers: `grep -n "PLANE_REPAIR_HOLD = "
toolkit/authsrv/authsrv.py`, not `authsrv.py:4383`. Every line-number anchor in the older
half of this file, and all four in `PLAN.md` §7 Q13, is already dead.

---

*What follows is the 2026-08-19/20 record — the warp mechanism decode and the candidate
graveyard. Its mechanism sections are still the best statement of the snap and are
largely current; its status claims, its `--router` verdict and its line-number anchors
are not. Read §A above first.*

## 0. Before your second command

```bash
git rev-parse --show-toplevel
```

**This bit us on 2026-08-19 and cost a client run.** Work landed on `main` while
the operator ran from a worktree that was 16 commits behind; the flag under test
did not exist in the tree they executed, and `authsrv.py` answered
`unrecognized arguments: --client-endpoint`. A stale tree does not error, it runs
old code. If you land anything on `main` while the operator is running from a
worktree, **fast-forward the worktree in the same breath**.

Three more traps that have each cost a run:

- **`movetap.py` pins build 38797. `session.py --exe` defaults to the NEWEST
  build under `vault/run`, which is 38833.** Always name the exe:
  `--exe "C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe"`. Do not reach for
  `--any-build` without diffing first. **That gate was INVERTED and is now REPAIRED
  (2026-08-19).** It refused the legitimately patched 38797 we actually launch —
  three extra patch sites (`0x508E2`, `0x50905`, `0x3DB4CE`) that the single
  hand-typed `patched` hash predated — while the stale `-c2`/`-probe` copies passed,
  and 38833 had no patched hash at all. `Build.patched` is now a TUPLE of accepted
  digests per build: the current patcher's 38797 copy and both 38833 copies are
  committed in `pinned.BUILDS`, and `make_custom_client.py` and `make_run_dir.py`
  each call `register_patched()` into `vault/client-patched/patched_digests.json`
  after their own verification passes. Registration REFUSES a digest equal to any
  known build's pristine, and under `strict` refuses what it cannot diff against a
  pristine image at all. `test_pinned.py` (143 checks, floor 130) and
  `test_buildid.py` (42, floor 39) hold every one of those refusals.
- **`--game-args` needs the `=` form for a single flag.** `--game-args='--foo'`.
  argparse reads a value starting with `-` as another option unless it contains a
  space, so two flags happen to work and one alone dies.
- **Bash heredocs in this environment eat backslashes.** A `\\n` reaches Python as
  a real newline. Write patch scripts with the Write tool, and put scratch in the
  session scratchpad — `/tmp` is `AppData\Local\Temp`, whose `sys.path[0]` has held
  a stray `dis.py` that shadows the stdlib module capstone needs.

---

## 1. The mechanism, stated once

**The warp is a RESYNC, not a teleport** — and as of 2026-08-19 every step of it
is named in the client binary. Full derivation and addresses: FINDINGS' last
section. The short form a cold session needs:

`movetap` reads the **sync** array (`[agentMgr+0xE8]`, ArenaNet's own name via
`AgMsg.cpp` asserts) — the server-authoritative agent our `0x0029` grants steer.
The client renders and reports from the **async** array (`[agentMgr+0x14C]`), the
copy it predicts. Two objects, two world clocks.

1. **We grant, the copy glides, then PARKS.** Speed is baked at grant time:
   `0x005FE950` computes `+0x48 = +0x58 + trunc(dist*1000/(maxSpeed·moveSpeed))`
   and velocity `+0xB0/+0xB4 = unit(d)·speed`. The dead-reckoner `0x005FFB40` is
   only `pos = +0x78 + vel·((t − +0x58)·0.001)` — **it never reads the speed
   fields**, so a mid-flight `0x002B` changes nothing about the current leg.
   In the default build the copy is parked **93.4 of 177.3 s**.
2. **Nothing we send afterwards reaches the rendered copy.** `0x0029` and
   `0x002B` are SYNC-ONLY. `0x0025` looks like it reaches both — but its async
   arm is gated: `0x005FD5D3` skips it when the agent id IS the
   client-controlled agent (`[mgr+0x1E0]` = AgTrack+0x14, set when the client
   registers its own local move, cleared only on removal). **Once the player has
   moved locally, our `0x0025` writes the sync copy only.** Independently
   confirmed numerically: including `0x0025` in a forward simulator of the copy
   made the residual 11× worse. Ungated both-copies messages: `0x0024`,
   **`0x0027`**, **`0x0028`**, **`0x002C`**.
3. **Nobody is watching.** The desync test `0x00605FC0` has **exactly 3 callers
   (0x005FEBEB in the grant bake, 0x006022A1, 0x00602BBD) — all message-driven,
   never per-frame.** So separation grows unchecked: the default build sat
   **127 intervals / 93.4 s at p50 1,522 u, max 3,648 u, with zero snaps.**
4. **Then it is redeemed all at once.** On the next grant or arrival,
   `0x006055E0` asks first whether the SYNC agent's own dead-reckoned position
   (`+0x78`) lies within 100.0 u @0x00946560 of a segment of the client's
   **history** chain — if so, **no snap**. ⚠ That operand is **not our grant**
   and the chain is **not a prediction**; both were decoded on 2026-08-20 and
   both killed §4's starred shape 1 (FINDINGS, "the AgTrack match test is
   decoded"). Otherwise it dead-reckons both copies — the SYNC one on the sync
   clock, the ASYNC one on the async clock — and runs **three gates, any one of
   which snaps** (FINDINGS 2026-08-20 round 2):
   **(1)** straight-line separation (`0x00709990` with `0x006057C8 push 1` =
   straightOnly; the *100 u* test is the walkable one, `0x00605C40 push 0`)
   compared against **300.0f @0x00946564** — effective cut **299.332591 u**,
   so exactly 300.0 u snaps; **(2)** `0x00709E90`'s `pathCount == 0`, which
   means the position our grant wrote is **off the navmesh**; **(3)**
   `0x005FEF70` returning 0 — the sync agent cannot take a first step toward
   the path, blocked by terrain or another agent's personal space.
   Any of the three resyncs **every** async agent via `0x006022B0`, a hard
   SetPosition — one agent failing the gates reseeds the whole roster.
   **That is the warp.**

**The harm, on the build we ship** (`20260819T145717` + movetap `145939`,
n = 251 paired reports): separation **p50 1,164 u, p90 2,163 u, max 3,648 u**;
snap cadence 2.67/min, inter-snap p50 21.7 s, max 41.2 s; 6/6 snaps collapse the
gap (p50 2,069 → 24.5 u) on two independent sources.

**Superseded — do not re-derive, do not re-quote:**
- The **125.9 u / "under 150 u" separation bound is `171153`'s, a REFUTED
  configuration.** The shipped build is ~1,164 u. (And do not attach a "9×"
  multiplier: the second parser's 1,516 u reads `movetap point`, which is stale
  by up to a leg — a different quantity, not a corroboration.)
- `+0x48` is *not* "set once and never re-armed" (304 re-arms in 61 s under
  `--heading-grant`); "stacked grants come due almost immediately" is the tail
  quoted as the rule (p50 2,890 ms, 6 of 304 under 200 ms).
- The `+0x48` arrival snap is nearly invisible on its own (7 arrivals landing
  0.0 u from `m_targetPoint`, visible jump 2.4-21.6 u) — arrivals matter because
  they *call the desync test*, not because they teleport.
- **"A speed term cannot bound frequency" is too strong.** True form: *not at
  0.66* (0% there; 36% at k=0.5, 91% at k=0.1).
- **"The client's own stop is not the trigger" was a check that could not fail.**
  Run in the direction that can fail, intervals *beginning* with a `0x0047`
  converge 4/31 vs 4/219 — a **7.1× lift**. Half the default build's snaps follow
  a client stop.
- **movetap is 9.4-12.9 Hz, not 50 Hz**, and its `now` is the client world clock
  (50 ms quanta, 1.3% slow vs wall). Any "20 ms interval" in the older record is
  a world-clock delta.

---

## 2. The scoreboard — five dead candidates

Read this before designing a sixth. **All five were additions, and all five chose
a point.**

| # | candidate | result |
|---|---|---|
| 1 | suppress the grant | retail sends 2,855 player-directed `0x0029`; not our invention |
| 2 | `--stop-echo` — echo the stop point on `0x0047` | warped anyway 9.9 s after an echo, and the echo dragged the player back |
| 3 | `--heading-grant` — re-grant on every heading | **caused warps.** 12.8/min |
| 4 | "echo the client's own vector" | a **no-op**: retail's `reported + vec2 + 0.5` and our `state["pos"] + heading` are the same expression |
| 5 | `--client-endpoint` — the client's own unclipped endpoint, refreshed | **REFUTED, worst of the three. 14.6/min** against a stated bound of 2 |

| 6 | the direction factor (`0x002B` 0.66 backward) | **DEAD on the shipped build: −3.1% magnitude, 0% frequency**, two independent derivations. Correctly aimed only at the refuted high-grant arms (−50.5% on `--heading-grant`) |

**Both flags default off and must stay off.** Also struck, with reasons in
FINDINGS: any backward/direction guard (retail has none — 25 of 29 backward
grants point behind the player's facing); the `+0.500 u` constant as a fix
(real, but it moves the arrival tick 2 ms against a 5,238 u harm); a `k ≤ 1`
clamp "bounding any warp to 768 u" (false — it bounds against the server's own
`p`, whose drift is a median 538 u and a max 1,429 u); `0x0028
AGENT_STOP_MOVING` at keyboard onset (retail does it in 1 of 499 onsets, and
that one was a zone transfer); and **`0x0027` at spawn** (a measured no-op — the
client already holds maxSpeed 288.0 / moveSpeed 1.0 in 4,115/4,115 samples).

⚠ **"The default build is 5.7/min and is the best configuration this repo has"
NO LONGER STANDS AS WRITTEN.** The 300 u bar counted ordinary walking; on the
repaired two-arm bar the three configurations read **7 / 20 / 13 hard rows** and
**1.31 / 5.69 / 11.88 per minute of span**. But observation coverage is
**31% / 72% / 89%** across them, and per *observed* second the ranking inverts to
4.19 / 7.48 / 11.27 jumps per min — the 4.19 stands (the default build's count did
not move), but 7.48 and 11.27 were computed from the PRE-REPAIR 19 and 11 and must
be re-derived before they are quoted — and 137.8 / 69.5 / 101.4 u displaced per
second, so **the default build is the worst on displaced distance and the best on
frequency-per-span.** It also trades many small warps for few enormous ones
(magnitude p50 **1,969 u vs 569 / 582**, max 3,405 / 768 / 754 u, on the repaired
bar; the pre-repair pair read 549 / 403). Say which denominator you
mean, every time; re-derive with the repaired `movesync.py` before comparing
anything.

---

## 3. Where the evidence points now

**Not the point, and not the speed. The STALENESS — and the fact that nothing we
send can reach the copy the player sees.**

The speed contest is CLOSED, both halves. Naming: `0x002B` = `direction_factor ×
modifier` (1.00 fwd / **0.66 back** / 0.75 side, × snare), locked to its own
trailing byte 0/1,049 violations; the absolute base rides `0x0027` (288.0, boost
383.04). Causation: **the client applies the direction factor locally** — our
runs backpedal at ~186 u/s (0.659× forward) while we send 1.0 in 621/621 sends,
and retail's own steps split 189.6 u/s at rate 0.660 (n=17) vs 189.9 at rate
1.000 (n=10). The wire rate never reaches the rendered copy. And on the
authoritative copy the binary says the glide **never reads `+0x60`** — speed is
baked into velocity and the arrival tick at grant time. Worth ≈3% of magnitude,
0% of frequency, on the build we ship.

**The separation budget says why.** Default build, 712 measurable intervals:
49.6% of growth accrues while the authoritative copy is **PARKED** and the client
walks away; 47.7% while both move; the BACK family carries only 30.4% of growth
and 10% of the copy's travel. (`--heading-grant` is a completely different
budget — 99.3% AUTH-MOVING, 95.9% of it BACK — which is why the 0.66 fix scores
well there and nowhere useful.) ⚠ 79% of the default build's net accumulation
sits in UNCOVERED time, so the table speaks for 21% of the run.

**The lever list, from the binary.** Messages whose async arm is unconditional
for the player's own agent: **`0x0024`, `0x0027`, `0x0028`, `0x002C`**. Not
`0x0029`/`0x002B` (SYNC-only by design), and **not `0x0025`** — its async arm is
gated shut once the player has moved locally. Anything that must correct what
the player *sees* has to come from that four-message list, or from making the
snap not fire at all (§4 item 1).

---

## 4. The next thing to do, in order

**Items 1–4 of the old list were run on 2026-08-19** (FINDINGS, "the corpus pass
on the handoff's list" — every number adversarially re-derived). Outcomes: (1)
**NO** — retail never stops on keyboard onset (1 of 499 onsets, and that one was
a zone transfer; retail's shape is supersession at one RTT, and its only
subtractive move is a zero-length grant answering the client's own `0x0047`);
(2) therefore **the subtraction branch never opens — do not build the
`0x0028`-at-onset fix**, and do not build supersede-every-heading either, which
IS dead candidates 3/5 (both already ran a TIGHTER leash than retail and warped
more — the point is bracketed from both sides and is not the free variable);
(3) resolved at the naming level, causal step open — see §3; (4)
`20260811T173940` was an instrument artifact (the client walked; pre-2026-08-19
captures logged only the `0x0047` stop arm, hiding 130 of 158 positions), but
the impossible-step population in OUR gamesrv corpus is live and larger: **26
unattributed detections** across 7 captures, one of them the default build —
quoted as magnitude and **excess over the 288 u/s budget** (excess p50 671 u,
max 3,804 u over the corpus's n = 43 detections), never as the implied velocity
this line used to carry, which §6 retires and the repaired `movesync.py` demotes
to a labelled gate input.

**That list was then run in full on 2026-08-19** (FINDINGS, "round 3 — the
mechanism is decoded"). Snap trigger: neither timer nor free-running threshold —
message-driven evaluation of a 300 u straight-line test (§1; it was recorded as
"walkable-path" until 2026-08-20 — the walkable conjunct is the 100 u one). Default-build harm:
measured at last, p50 1,164 u (§1). Scoreboard: rebuilt, and the denominators
turned out not to be comparable (§2). Handler statics: **done, and they decided
the causal question** — speed is baked at grant time, `0x0025` is gated, `0x0027`
/ `0x002C` reach both copies (§3). Impossible steps: 25 of 26 are resyncs; the
survivor is a client-side click-move at 2.6× the walk budget. `pinned.py` and
`movesync.py`: **repaired this round** (see §5 and TESTS.md).

### The three shapes worth trying next, in order of evidence

1. **★ ANSWERED 2026-08-20 — and the answer RETIRES this shape.** `0x00605AF0`
   compares **POINT ONLY**: no time, no sequence, no id. (The whole 145-instruction
   body holds exactly one integer `cmp` and it is `sub esp, 0x30`; one absolute
   memory read, and it is the 0.99 constant.) It asks whether a point lies within
   **100.0f** of a segment — **straight-line perpendicular, compared SQUARED and
   STRICT**, *and* within 100.0f of **walkable path length**, compared **LINEAR and
   INCLUSIVE** (**99.919968 u** effective — exhaustive over 2,048,001 float patterns
   of the LUT sqrt, FINDINGS round 5; ~99.6 was a scaled worst case). Full decode:
   FINDINGS, "the AgTrack match test is decoded".
   **BUT THE POINT IT TESTS IS NOT OUR GRANT, AND THE LIST IS NOT A PREDICTION.**
   `0x00605643` reads `source+0x78` — the SYNC agent's own position, dead-reckoned to
   the client's clock by `0x005FF880` during the grant bake. Our `0x0029` writes
   `+0x88..+0x94` and `+0x80` and **never `+0x78`** (n = 0 writes in `0x00602A40`'s
   body). And the chain is ArenaNet's `history`: nodes stamped `now` at creation
   (`0x00604DCC`), pushed on the FRONT (`0x00605A93`), one per movement-command
   change with a forced 2.5 s re-sample — so a single click yields a **one-segment**
   polyline. ⇒ **There is no grant we can send that makes this match by
   construction**, and the wire already agrees: `--heading-grant` sat 0.5 u from the
   client's own endpoint (193/193) and is recorded REFUTED at `authsrv.py:1046` for
   CAUSING warps; the click-only capture held 40 grants at 0.0000 u and still logged
   7 hard jumps up to 3,405 u. **Do not build "make the grant match".**
⚠ FIRST, A LOCATION CORRECTION: the "next job" sentence is **not** in `HANDOFF.md` §4 (which is "Prior art — what to take, what to ignore" and contains no such sentence). It is **`PLAN.md`:1417**, the closing clause of §"Movement — the AgTrack match test is DECODED and shape 1 is DEAD (2026-08-20)". `grep -rn -i "next job" HANDOFF.md PLAN.md` returns that one line and nothing else. Replace the clause that currently reads:

> "…and the next job is the undecoded fallback half `0x00605753`–`0x0060583D` where a MISS is actually adjudicated (and the 300.0f gate there is STRAIGHT-LINE, correcting FINDINGS:2373)."

with:

> …and the fallback half `0x00605753`–`0x0060583D` is now DECODED (2026-08-20): a miss is adjudicated by **three** gates, all snapping on failure — straight-line separation over **299.3326 u** (not 300; `0x0046E870`'s LUT sqrt is a one-sided over-estimate, so exactly 300.0 u SNAPS, correcting FINDINGS:2861's ~298.8 u), OR a **walkable** navmesh query returning `pathCount == 0`, which means **our granted SYNC position is off the navmesh**, OR `timeToEvent < 0.0005f` on the first step — so **separation under 300 u is NOT sufficient to avoid a snap**, and the snap itself is a reseed of **every** agent in world 1, not the player jumping. **No gate is a server lever**: gate 1's async operand is written by none of the movement messages (9 of 17 AgMsg handlers touch world 1; `0x0029`/`0x002A` do not), gate 2's failing operand is the point we granted tested against a navmesh we lack, and gate 3 reads neighbouring agents and terrain. **The next job is therefore not another decode but a measurement and a costing**: (a) log `rec.clientControlled` at `[agentMgr+0x1CC+0x20]+id*0x1C` alongside separation to find which gate actually fires — the gates are fenced behind `clientControlled != 0` and `world == 0`, which may explain Lane D's 92.7% above-threshold-no-snap on its own; and (b) price `0x002C`, the one real lever (its handler clears the record then writes **both** copies, so no gate runs), against the record that an earlier build sent five and they were removed as "the warp the player described" (`authsrv.py:7036-7045`). One loose end remains: `0x005FCAA0` is a second, gate-free snap route fired from local input. (The Tier-2 `*pathCount` hole was closed in round 3 — that leg is a `PathEngine.dll` the install does not ship.)

> **★ UPDATED 2026-08-20, round 3 — and the update mostly REMOVES work.** The two other callers of gate 2's query and gate 3's predicate are now decoded (`studies/movement/FINDINGS.md` §"round 3"). **`0x00709E90`'s other caller is `0x0081ADB0`, the LOCAL PLAYER's own move-to-point planner** (ChCliBase.cpp:248 `this == context->playerControlledChar`; input-driven, 19 functions / 32 edges upward, 0 in the AgMsg receive region with a 3/3 positive control — a controlled negative, **not** a proof, since `--xrefs` cannot see indirect calls). **`0x005FEF70`'s other caller is `0x00600500`, AgAgent's one-shot obstacle-sidestep computer**, and **both callers treat a zero return identically** ("that step is not takeable", discard the position under test, n = 2 of 2) — **the arc did not over-generalise the predicate.**
>
> **Three things this DELETES from the next-job list.** (a) The **4-vs-9 maxCount asymmetry is incidental**: `*pathCount` is the emitted count (`0x007297B2`–`0x007297C3`), overflow drops silently through a void `pop esi / ret` at `0x00726623`, and the fallback returns truncated results unvalidated at `0x0070A0C6`→`0x0070A0CE` — a 5-corner corridor gives gate 2 `count = 4`, which is NO SNAP. (b) The **300.0f-vs-10000.0f arg3 gap is incidental too**: arg3 is a march *budget* whose exhaustion jumps to the SUCCESS exit, tier 2 substitutes `|to−from| + 0.5` (`0x00709FB1`) and never sees it, and gate 1 fences gate 2 inside 299.33 u so it can never bind. (c) **The Tier-2/provider `*pathCount` hole is INERT**: that leg is `LoadLibraryA("PathEngine.dll")` + `GetProcAddress` ordinal 1 (`0x00737380`, imports confirmed), and no such DLL exists in the owner's install (vault `MANIFEST.json`, `source_dir = C:\gw`, only `Accounts.json` excluded) — with a `LoadLibrary` search-path caveat, so evidence rather than proof. Tiers 0/2/3 write on every exit.
>
> **★ AND READ THIS BEFORE COSTING ANYTHING AGAINST GATE 2: it has n = 0 observed firings.** Gate 1 runs first and snaps above **299.332591 u straight-line**, so gate 2 is only reached below that — and this arc's own runtime lane measured **24 snaps over 623 paired intervals with 0 of 24 beginning below the gate, minimum before-separation 342.8 u straight-line.** Every snap we have ever measured is explained by gate 1 alone. **Gate 2 is knowledge, not a lever. Do not build a fix against it.**
>
> **What DID get sharper, and it is still not a lever.** `pathCount == 0` means **the START point could not be resolved on the navmesh** — narrower than "no complete path": all three exits of the deciding tier are start-conditioned, and an unreachable goal yields a non-zero PARTIAL path (`0x0072B4E8`). The cheapest way to defeat resolution is an **integer**: `0x0072AE4F cmp eax,[ecx+0x20] / jb` range-checks the start's plane against `staticData->map.Count()` (ArenaNet's own name, three sites on the same displacement) and returns NULL → `*pathCount = 0` at `0x0072B132`, no geometry touched. **But we do not fire it**: every plane our server emits is literal 0 (12 of 12 `map_static_config` rows) or an echo of the client's own report (`authsrv.py:2303`, inside `if accept:`).
>
> **NEXT, revised, in cost order:**
> 1. **UNCHANGED and still the only thing that decides anything** — the runtime measurement: breakpoint `0x0060580D` / `0x00605820` during a live desync, logging `rec.clientControlled` at `[agentMgr+0x1CC+0x20] + id*0x1C` alongside separation. It now answers a second question for free: **is gate 2 ever reached at all?**
> 2. **NEW, cheap, and the only measured defect this round produced** — assert the spawn-plane invariant. Re-run in-tree, **n = 12** configured maps: **8 OK, 1 PLANE-MISMATCH (map 474 — spawn (0,0), config plane 0, our geometry says plane 31 and only 31, out of 45), 3 OFF-MESH (55, 90, 194).** Map 474's is the in-range-but-wrong shape that defeats the start lookup with no error. ⚠ **Severity, honestly:** all four failures carry the placeholder spawn `(0.0, 0.0)`; **every map with a real spawn coordinate passes, 7 of 7**, and no map currently served fails. ~20 lines reusing `pathmap.containing` (the click arm already calls it), plus its `TESTS.md` entry.
> 3. **NEW, minutes** — two stale citations: `authsrv.py:2838` and `studies/smsg/FINDINGS.md`:1498 both still call `0x0029`'s plane fields UNVERIFIED against three independent binary derivations. Field 3 = destination plane (`agent+0x90`), field 4 = current plane (`agent+0x80`); CLICK_SWEEP variant 1 is correct and the experiment is closed.
> 4. **UNCHANGED** — price `0x002C`, still the one real lever, still against the record that an earlier build sent five and they were removed as "the warp the player described".
> 5. **NEW, priced not recommended** — make the **heading** arm plane-aware. It is 88.5% of 2,855 player-directed grants, it currently sends `(plane, plane)` and goes through the plane-blind `clip_to_walkable` (which *suspends collision entirely* off-mesh), and **retail does not tie the two fields**: n = 987 live `0x0029`, equal in 973, **differing in 14 (1.4%) — the plane transitions**. `pathmap.plane_at(x, y, prefer=cur_plane)` exists and is measured 189/198. **Stated failure mode: it is wrong ~5% of the time and wrong exactly at bridges and stairs**, which is where the reported symptoms live. Candidate to price, not a fix to ship — and a candidate for the *symptom*, never for gate 2.
>
> **And strike this document's "cannot avoid tripping it by design without map data."** We have the map data: `toolkit/mapdata/pathmap.py` reads `PATHING_CHUNK = 0x20000008` out of the owner's own `Gw.dat` at run time, extractor in-repo, layout credited in `PLAN.md` §6.1 and `THIRD-PARTY-NOTICES.md`, nothing committed. **Provenance is not the blocker on the navmesh route.** What *is* unmeasured is our path verdict against the client's own, which needs a client run; our mesh's agreement on the point-membership question is already measured at **189/198 exact plane matches** and **n = 532, 93.8% clean**.

2. **`0x002C AGENT_UPDATE_POSITION`** — the only catalogued primitive that calls
   `AgTrack::Clear` and then SetPositions BOTH copies, ungated. It is a hard set,
   so it is a teleport by construction; the open question is whether a small,
   frequent, correct one is cheaper than a rare 3,648 u one. We have never sent
   one in THIS corpus (0 of 2,024,792) — ⚠ but that is a census, not a history:
   `authsrv.py:7036-7045` records an earlier build that **did** send them ("five
   AGENT_UPDATE_POSITION went out and three were arrivals, carrying the client
   630, 189 and 765 units"), removed as "the warp the player described". Untried
   in the current corpus, not untried. Retail sends 12 corpus-wide, so this is rare-but-real
   in ArenaNet's own traffic.
3. **`0x0027 AGENT_UPDATE_SPEED_BASE` as a mid-flight re-bake** — worthless as a
   spawn constant, but it reaches both copies unconditionally AND re-issues the
   outstanding grant (`0x00602910` → `0x00602A40` → `0x005FE950`), so it is the
   only lever that can re-aim a stale in-flight destination without naming a new
   point.

Still open, and worth one measurement each: the `0x0025` async gate means the
predicted copy is unreachable **while a pending record exists** — does clearing
that record (item 2's `AgTrack::Clear`) reopen it? And the survivor step's
2.6×-budget click-move wants a movetap run over a long ungranted click-move.

---

## 5. How to score any candidate, in one minute

```bash
python toolkit/harness/session.py --keep-open --exe "C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe" --game-args='--your-flag'
```

Play for a minute — **hold S and click distant ground**, which is what reproduces
it — then:

```bash
python toolkit/clientscan/movesync.py --wire-only
```

**This needs no `movetap`, no build pin, no second terminal.** `movesync.py` was
**repaired on 2026-08-19** and now: reads the SPLICED `0x003D`+`0x0047` c2s
stream (the old source was the `0x0047` stop arm only, which on every pre-fix
capture hid ~80% of the client's positions); makes a **speed-gated hard-jump
count the verdict** on TWO ARMS — implied speed > 400 u/s at dt ≥ 0.05 s, and
**displacement ≥ 520 u BELOW that dt floor**, where a speed is not a measurement.
The second arm is what this round added, and it is retail-calibrated: retail scores
ZERO on both (largest sub-floor step 19.15 u over 82 intervals against a 520 u arm,
27x of headroom; largest step inside 2 s 517.87 u / 1.352 s), while the corpus goes
**61 → 64 hard rows over 961 captures / 4,582 intervals** — the three restored rows
being its fastest genuine events, all at ~32 ms. It also demotes the 300 u bar
to a labelled, refused legacy count; refuses on COVERAGE as well as median
cadence; prints no quotable RATE above its own refusal — and, the other half of
that rule, does not let a refusal SUPPRESS a COUNT either: under the
`MIN_INTERVALS` floor it prints the count, the magnitude and the excess with no
`/min` anywhere, because only a per-minute number needs a denominator.

⚠ **The old "anything at or above 5.7/min is worse than shipping nothing" bar is
RETIRED** — that number counted ordinary walking (retail scores 6.4/min on the
same rule with zero intervals above 400 u/s). Score on the hard bar, and **state
the denominator**: rate per minute of span AND per minute of actively-reported
time, because coverage runs 31-89% across configurations and the ranking inverts
between them. Two different "active time" thresholds are in play and they are
not interchangeable: the coverage / per-observed-second figures in this file and
FINDINGS use gaps ≤ 2.0 s, while `movesync.py`'s printed active-time rate uses
`FREE_SILENCE` = 1.042 s and prints the sweep beside it — say which one a number
used, every time. Quote **magnitude and rate together**, never one alone. For a
discontinuity, quote **magnitude and excess over the 288 u/s budget** — never
implied velocity, which is arithmetic on a denominator the event itself created.

For the separation number too, run `movetap.py --seconds 300` in a second terminal
once the map has loaded, then `movesync.py` without `--wire-only`.

**Standing rule for any warp run: keep the keyboard moving the whole time.** The
client emits `0x003D` only while moving, so a stationary wait blinds every
wire-side instrument exactly when the phenomenon fires — 8.7% of retail's own
grants sit outside any watched interval for this reason.

---

## 6. Traps this arc actually fell into

Not general advice — each of these cost something here.

- **Over-fitting, five times.** A rule drawn from the cases studied hardest, then
  used as a gate. The bit-exact landing rule suppressed a real 42 u teleport; a
  four-term precondition excluded 2 of 4 known warps; a probe design would have
  called every ordinary glide a teleport; and **a prediction that bounded teleport
  SIZE while the harm arrived as FREQUENCY shipped a fix that warped the owner's
  character.** State predictions in the units the harm arrives in, and bound both
  magnitude and rate.
- **Vacuous controls.** A no-collapse control in `test_movesync` judged **zero
  rows** — `all([])` is True — inside the section whose job is proving the checks
  can fail. Assert the row count first. Caught by reading output, not by the test.
- **Tautological comparisons.** The first wire-only test compared a point against a
  segment it defined, because where grants outnumber reports the grant-time report
  is often the *same record* as the pre-jump position. It read 0.0 u and looked
  like a refutation.
- **Instruments that score the wrong quantity, quietly.** `warpscan` said
  "NOT near any grant" for 10 of 12 detections; that line was the finding and read
  as a puzzle for two runs. `movetap`'s floor demanded 7,500 samples from a reader
  that sustains 13 Hz, so it printed FAIL over the run that overturned the arc.
  Both are fixed; the lesson is that a floor which fires on every healthy run is
  how a real FAIL gets waved through.
- **Believing a summary over the binary.** "The client normalizes it" was true of
  the `0x0025` jump table as a whole and false for its dominant case, which is a
  bare `mov`. Disassemble the case you are standing in.

Added 2026-08-19, each paid for in this arc's own rounds:

- **A NEGATIVE CAN BE VACUOUS TOO, and it looks like evidence.** "The client's
  own stop is not the trigger — 0 of 31" was structurally impossible to observe:
  every `0x0047` sits at a report-interval boundary, and an interval in which the
  client moved hundreds of units cannot END on a stop report. Run in the
  direction that CAN fail and the answer flips to a 7.1× lift. **Before quoting a
  zero, ask what a non-zero would have looked like.**
- **A COUNT PRINTED ABOVE A REFUSAL IS ALSO REFUSED.** `movesync` correctly said
  "REFUSING a verdict" at a 1.28 s cadence; the "5 unexplained jumps" printed
  above that line became the arc's "largest remaining hole" for a week. The tool
  now prints no quotable RATE above its own refusal — and the rule has a SECOND
  half the first repair got backwards: a refusal must not SUPPRESS a count either.
  The `MIN_INTERVALS` floor used to `return` before the hard section, so a
  nine-interval capture carrying a 3,000 u step printed a bare tally; a count and a
  magnitude need no denominator. But the habit is the fix.
- **THE DENOMINATOR IS PART OF THE MEASUREMENT.** Three configurations were
  ranked on jumps/min for weeks while their observation coverage was 31% / 72% /
  89%. Per observed second the ranking inverts. State span-vs-active every time.
- **AN IMPLIED VELOCITY OVER A WINDOW THE EVENT CREATED IS NOT A QUANTITY.**
  "23,279 u/s" was 740.7 u across a 32 ms window that existed only because the
  client emitted an extra report immediately after the snap. Magnitude and excess
  over budget survive; velocity does not.
- **A GATE THAT LOOKS SYMMETRIC MAY BE GATED ON ONE SIDE.** `0x0025` is
  classified as reaching both agent arrays and does — for every agent except the
  one the client controls. A per-opcode census that stops at "which arrays does
  this handler touch" gets the player's own case exactly backwards.
- **CALIBRATE THE SAMPLER BEFORE QUOTING ITS UNITS.** `movetap` was recorded as
  50 Hz and is 9.4-12.9 Hz; its `now` is a world clock running 1.3% slow in 50 ms
  quanta. A whole round's "20 ms intervals" were world-clock deltas.
- **A FIX'S OWN REVIEW IS NOT OPTIONAL.** Both instrument repairs this round came
  back FIX-FIRST from an adversarial reviewer: the `movesync` speed gate silently
  dropped the corpus's three fastest real events, and the `pinned` digest-set
  change accepted 10 MB of random bytes as "patched" when the pristine image was
  absent. Both were caught by re-running the attack, not by reading the diff.
