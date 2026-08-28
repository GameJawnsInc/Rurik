# HANDOFF — the warp hunt, from a cold session

**Written 2026-08-27 at commit `7ed5704`. REVISED 2026-08-28: R1 is DONE and this file
was wrong about it.** Read this before proposing anything: the mechanism is settled,
**seven** server-side candidates have been measured, and the four that looked most
obvious are all refuted with numbers attached.

**The 2026-08-28 pass changed three things a cold reader must not miss.**

1. **§4's R1 is closed** — `FINDINGS.md` §1p. Retail's click contract is now measured
   end to end, and **`--click-echo` turns out to be retail's own answer for the majority
   class**, matched bit-for-bit on 13 of 13 scorable clicks. It was never a heuristic.
2. **The live next-actions list is `FINDINGS.md` §1p.10, not §4 of this file.** Its top
   two items are DESK changes that each delete a refusal: stop dropping clicks that
   arrive under keyboard authority (retail answers **7 of 32** such clicks; we drop
   them), and delete the 1.0 s freshness gate on the echo path (retail answers with
   reports up to **20.99 s** old, and on 5 of 32 clicks with no position ever reported).
3. **This file previously said of R1 "Nobody has ever looked", and that was false when
   written** — `studies/movement/ROUTER.md` §1 had measured it two days earlier, and
   `FINDINGS.md` §1n.4 cited it. It cost five agent-lanes. **Before you price any route
   in §4, grep the tree for it.**

---

## 1. Where it stands, in one paragraph

The client keeps the player agent **twice** — a `WORLD_SYNC` copy driven only by our
wire grants, and a local copy driven by the client's own path solver. When they diverge
past ~300 u the client reconciles by **dragging the local copy onto the sync copy**,
which is the warp. Three server-side movement policies have now been measured against
the same map, operator and instrument:

| policy | largest displacement | total | verdict |
|---|---|---|---|
| shipped — refuse the click | **5,970 u** | 8,040 u | warps to spawn |
| **`--click-echo` (MOVECODE-K2)** | **446 u** | **1,101 u** | **best measured** |
| `--router` | 2,127 u | 3,276 u | REFUTED, §1o |

`--click-echo` is the current recommendation and is **off by default**. Its residual
harm is **no-clip**: the character walks through props along the straight line to the
clicked point. A displacement counter cannot see that — no-clip is a legal walk at
288 u/s with both `m_point` and its `+0x58` stamp advancing.

**2026-08-28 — the echo is now known to be RETAIL'S OWN ANSWER, not a lucky heuristic**
(§1p.8). Retail echoes the bit-exact click point on **19 of 32** live clicks, and on
**13 of 13** scorable ones our mesh independently agrees a single leg suffices, so on
that class we reproduce ArenaNet bit-for-bit. On the other class we reproduce **0 of
11** — retail's part-way waypoints are bit-exact navmesh trapezoid corners, and no
policy this arc has built emits one.

**The no-clip is also now counted, and it is not occasional**: replaying the K2 run's
own 8 echoed clicks, **7 of 8** granted a straight line our own mesh calls blocked
(median shortfall ~2,300 u) — and all eight are labelled `clear line` in the server log
by a **hardcoded string** (§1p.11). Fix that label before trusting any audit of it.

**The residual is mesh AGREEMENT, not mesh correctness.** Whatever we grant, the
client's own solver disagrees and the reconcile drags the body onto our answer. The
only grant it cannot disagree with is the destination it chose itself — which is why
the bare echo wins. **That now has a fourth independent confirmation** (§1p.12): every
server-side lever that consults our navmesh is capped by how well it agrees with
ArenaNet's, and the echo is the only one that never consults it. **It is still an open
question whether anything server-side closes the rest, and R1 could not settle it** —
retail's chains come off the client's own mesh by construction.

---

## 2. Read in this order

1. **[FINDINGS.md](FINDINGS.md) §1p** — what retail actually does, measured offline
   over 61 live connections. **§1p.10 is the live next-actions list.** §1p.9 lists the
   six lanes that came back vacuous or underpowered and is the most method-dense part.
2. **§1i and §1j** — the mechanism, from the capture and from the binary. §1j.1 proves
   the direction (state flows sync → local), §1j.3 is the pin that makes the twin
   freeze, §1j.7 is the compiled-in two-world asymmetry.
3. **§1n and §1o** — the two most recent runs and what they refuted.
4. **§1l and §1m.1** — a worked example of me blaming the wrong thing and the log
   correcting it. Read it for the method, not the content.
5. **`authsrv.py`'s graveyard block** (search `HEADING_GRANT`) — five earlier
   candidates with their epitaphs, plus `CLICK_ECHO`'s own reasoning. **Read it before
   proposing any policy**: a clip-gated grant was proposed on 2026-08-28, and
   `--heading-grant`'s epitaph had already killed it in one sentence (§1p.12).

`PLAN.md` §3 is the status authority. `PLAN.md` §7 Q13 is the open owner decision
(whether to adopt the `D1_LEAD` bundle) and is **not** blocking any of the routes below.

---

## 3. Do NOT rebuild these

Each was measured and each is in the tree with its numbers, deliberately, because a
refuted candidate carrying its measurement is worth more than a deleted one.

| candidate | why it died |
|---|---|
| `--heading-grant` | refreshed FASTER than retail (0.32 s) and still warped: point computed from `state["pos"]`, and clipped to our navmesh |
| `--client-endpoint` | met both its terms and warped MORE (14.6 jumps/min vs 5.7) |
| `--keepalive-grant` (K1) | INERT — 2 fires in 1,773 verdicts. §1l.4's claim that it *caused* the spawn warps is **withdrawn** by §1m.1 |
| `--router` | 4.8× worse than the echo alone; re-granted the same first leg 4× |
| **MOVECODE-K3** (route from `_sync_position`) | **withdrawn before being built** — the router's origins are on-mesh and its routes are valid, so a better origin yields a *different* valid route the client still disagrees with |
| **clip-gated echo** (gate the echo on a clip from `_sync_position`) | **REFUTED at a desk 2026-08-28, §1p.12** — replayed against K2's own 8 echoed clicks it refuses **7 of 8**, i.e. a near-total revert to the shipped refusal. `--heading-grant` had already granted a clipped point and its epitaph names the clip as one of its two failures |
| **one-leg-gated echo** (echo only when our mesh says one leg suffices) | **NOT WORTH BUILDING, §1p.8** — buys **0** additional bit-exact matches against retail (13/26 either way); its only win is not granting an off-mesh line in 11 of 26, into an else-branch that is either `--router` (2,127 u) or refusal (5,970 u). A gate whose false branch is a refuted policy is a refuted policy with extra steps |

**The pattern across all five — now seven — candidates:** every candidate that asserts
*more* about where the player should go does worse. The winner asserts the least.
**2026-08-28 sharpens why, and it is not a maxim about modesty:** every lever except the
bare echo consults our navmesh, and our navmesh agrees with the client's on ~35.7% of
clipped stops on map 280 (`ROUTER.md` §3). The echo wins because it is the only answer
that never consults it — and because it is, on the majority class, exactly what ArenaNet
sends (§1p.8).

---

## 4. The open routes, cheapest first

### R1 — What does retail actually do during a click-walk? **DONE, 2026-08-28 — see §1p**

> **THIS ROUTE IS CLOSED. What follows is the corrected record; the original text said
> "Nobody has ever looked" and that was false when it was written.** `FINDINGS.md` §1p
> is the answer, and §1p.1 quotes the sentence it replaces. The cost of the error was
> five agent-lanes re-deriving a committed measurement — the exact failure the top of
> `CLAUDE.md` is about, committed by a handoff whose own source section (§1n.4) already
> cited the document that had the answer.

**Mostly already looked at, and the record is `studies/movement/ROUTER.md` §1/§3.**
`python toolkit/clientscan/routerbench.py --census` reproduces it in one command and
still did on 2026-08-28: ≥29 attributed clicks, ≥16 verbatim / ≥13 part-way, every one
answered within one RTT.

**What §1p added, all offline:**

* **Retail answers every click from a position it does not have.** 32 of 32 c2s clicks
  answered within 0.065 s, while holding a report older than 1.0 s on **22 of 32**,
  older than 10 s on 13, and with **no client position ever reported on 5 of 32**. Our
  `fresh <= 1.0` gate (`authsrv.py:16583`) models a precondition retail does not have.
* **The answer is the bit-exact click point (19 of 32) or a part-way waypoint (13 of
  32)**, and those waypoints are **bit-exact navmesh trapezoid corners** in our own
  decode (13 of 19 distinct), not points on the player's ray.
* **`--click-echo` is retail's answer for the majority class.** On 13 of 13 scorable
  verbatim clicks our mesh independently says one leg suffices; we match bit-for-bit
  there and **0 of 11** on the other class. The echo is not a lucky heuristic.
* **Does retail's client report position during a click-walk?** *Quieter, not silent* —
  and **our own committed answer was overstated**: `REALFIX.md` §0.18,
  `routerbench.py:180-182` and `authsrv.py:5044` all state the silence as absolute, and
  the two instruments built to re-measure it **could not return a non-zero** (their
  window terminator set contained the opcodes they counted). See §1p.4; fixing those
  three sites is item 6 of §1p.10.

**What R1 could NOT do, and the original text was wrong to claim it could:** tell us
whether the residual no-clip is *unavoidable*. Retail's chains come off the mesh the
client agrees with **by construction**, so measuring them bounds nothing about ours.
That question is R4's and always was.

**The live next-actions list is now `FINDINGS.md` §1p.10**, ranked, each item with its
cost and its refuting clause. Its top two are DESK changes that each *delete a refusal*.

### R2 — WHICH gate fires? **Gate 2 needs NOTHING; gate 3 is one content row**

`snaptest` (`0x006055E0`) has three gates and only **gate 1** was ever confirmed
(separation, §1h.1). **Gate 2 is already observable in captures we hold** — §1p.13:
`movehook` taps `MapFindPath`, gate 2's call is `00605802 call 0x709e90`, so a captured
query returning to `0x00605807` is that call site executing, and there are **9 such
executions across 5 distinct movehook captures**. Each is a witness to a **gate-1 pass**.
(Not the same quantity as `PLAN.md`'s starred "gate 2 has n = 0 observed firings", which
counts which gate *decided* a snap — but that line is dated 2026-08-20 and four of the
five captures post-date it.)

So the remaining cost is **gate 3** alone (`0x005FEF70`) — verified to be a real
`push ebp` entry, one row in `content/movecode.toml` and a `gensites.py` regenerate,
exactly like the sites added for B3.

**Before touching this, read `studies/movement/FINDINGS.md` §3117–3143**, which already
decodes the whole function including the polarity (**`1 = NO SNAP, 0 = SNAP`**, from the
sole caller). A session on 2026-08-28 disassembled it cold, concluded the gates were an
AND rather than "any one snaps", and was refuted — the accept path *is* an AND, which is
the same statement as "any one gate snaps" on the failure path (§1p.13).

**Why it matters:** if the no-clip reconciles are firing on gate 3 rather than gate 1,
then separation is the wrong thing to manage and every policy above was aimed at the
wrong gate. That is a cheap, high-information check.

Also unhooked and cheap: `agent+0x24` (the world field) — currently the sync side is
identified indirectly from `reseed`'s source argument.

### R3 — Can the reconcile be SUPPRESSED at all? **Static, cheap**

If some flag or message makes the client stop reconciling, the entire class disappears
and no grant policy is needed. Named but unexplored:

* `INTERNAL_FLAG_MOVEMENT_STALE` — m_flags bit 19 (`0x80000`), §1j.3
* `INTERNAL_FLAG_IN_WORLD` — bit 17 (`0x20000`), the precondition the advance routines
  actually test
* `agent+0x98` — the single field separating `0x002A` from `0x0029`, meaning still
  UNKNOWN (§1c.5, and `MOVECODE-Q3`'s premise was refuted in §2.2)

**Refuting shape:** if every reader of those bits is cosmetic, this route is dead in an
afternoon and we have lost nothing.

### R4 — Mesh agreement. **The long road, and the only one aimed at the residual**

`MOVECODE-Q2`: our decode of map 280 has holes — 2 of 20 `MapFindPath` queries OFF-MESH,
bounded to y ≈ 6,900–8,500 (§1h.4), and 4 of arm A's 17 click refusals were geometry,
all in that region (§1i.5). This is the only route that addresses "our route is not the
client's route" head-on rather than routing around it.

Note what R4 is **not**: §1o showed our routes are *valid* — legs clear, shortcuts
genuinely blocked. So this is not "fix broken routes"; it is "make our mesh agree with
theirs", which is a much larger claim and may not be worth it for a mod platform
(`PLAN.md` — fidelity is per-map effort, not extraction).

---

## 5. The instruments

| tool | what it gives you |
|---|---|
| `toolkit/clientscan/movehook/attach.py --minutes N --out DIR` | inject the hook into a running client; the DLL creates the directory |
| `readhook.py --bin DIR/movehook.bin` | the world-copy census (per-object motion, grant gaps, **displacements with magnitudes**), P1a, the snap section |
| `keepalivelog.py` | server side: click verdicts answered-vs-refused, K2 echoes against their exposure floor, **router rows and repeated-leg detection**, grant/tick rates |
| `pathdiff.py --map 0x287B3 --bin …` | replays captured `MapFindPath` queries through our mesh |
| `codescan.py --dis/--xrefs/--field` | the binary |

**The scoring number is `largest displacement`**, printed by `readhook`. A reseed that
*fires* is not a warp — run 5 had 14 reseeds and 2 displacements.

---

## 6. Traps that cost this session real time

* **One agent id names TWO objects.** Never filter a trajectory on `id == 1`; group on
  the `ecx` address. `readhook` does this and raises if you are about to. It invalidated
  a whole prior analysis (§1h.2).
* **A subcount that reads clean.** §1k.3 registered "displacements *following a reseed*"
  and it printed **0** while the operator watched two spawn warps — both went through
  the *teleport* arm. Lead with magnitude and total.
* **`if dt > 0` deletes exactly the teleports** (position moves, stamp does not).
* **Denominators must match on both sides** of any normalised rate.
* **Runsheet commands must be PowerShell or `python`.** A bash `cp` broke a run at the
  operator's terminal *after* the walk was done.
* **`--map auto` refuses on these captures** (two meshes tie at 95.0%); pass
  `--map 0x287B3`. The server log's `map_id 148` is the client's connect parameter, not
  where the session ran — the spawn coordinate `(−6036, −2519)` is the tell.
* **The hook DLL does not unload.** Close the client before rebuilding, or `LNK1104`
  leaves the old site set on disk.
* **When the operator's report disagrees with a metric, the operator is right** and the
  metric has a blind spot. That happened twice here and both times the blind spot was
  real.

---

## 7. Running an arm

`studies/movecode/RUN-K2.md` is the worked template — predictions and refuting clauses
first, an exposure floor, then the commands. Copy its shape.

```bash
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 900 --game-args="--click-echo --map 280"
```

`--exe` is not optional: `session.py` defaults to the newest build and every movehook
address is **38797**. Announce the launch — the client fights for input focus and the
machine is shared. **The operator drives**; world-anchored clicking is not agent work.

**Pre-register an exposure floor for every arm.** K1 arm A fired twice and §1l reported
through it anyway; that is the mistake to not repeat.
