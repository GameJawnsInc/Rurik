# HANDOFF — the warp hunt, from a cold session

**Written 2026-08-27 at commit `7ed5704`.** Read this before proposing anything: the
mechanism is settled, **seven** server-side candidates have been measured, and the four
that looked most obvious are all refuted with numbers attached.

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

**The residual is mesh AGREEMENT, not mesh correctness.** Whatever we grant, the
client's own solver disagrees and the reconcile drags the body onto our answer. The
only grant it cannot disagree with is the destination it chose itself — which is why
the bare echo wins. **It is an open question whether anything server-side closes the
rest.**

---

## 2. Read in this order

1. **[FINDINGS.md](FINDINGS.md) §1i and §1j** — the mechanism, from the capture and
   from the binary. §1j.1 proves the direction (state flows sync → local), §1j.3 is the
   pin that makes the twin freeze, §1j.7 is the compiled-in two-world asymmetry.
2. **§1n and §1o** — the two most recent runs and what they refuted.
3. **§1l and §1m.1** — a worked example of me blaming the wrong thing and the log
   correcting it. Read it for the method, not the content.
4. **`authsrv.py`'s graveyard block** (search `HEADING_GRANT`) — five earlier
   candidates with their epitaphs, plus `CLICK_ECHO`'s own reasoning.

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

**The pattern across all five:** every candidate that asserts *more* about where the
player should go does worse. The winner asserts the least.

---

## 4. The open routes, cheapest first

### R1 — What does retail actually do during a click-walk? **OFFLINE, no client, highest value**

**Nobody has ever looked.** Three policies were invented and measured against each
other; none was compared against ArenaNet answering the same situation. The vault holds
**37+ live connections** and the tooling already decodes both directions
(`toolkit/authsrv/cmsgstream.py` for c2s, `tape.py` + `codec` for s2c).

Two questions, both answerable at a desk:

* **Does retail's client send position during a click-walk?** Ours does not — that is
  measured, and it is why `geo-stale` is unsatisfiable (§1m.2). If retail's client
  *does*, something we send (or fail to send) suppresses it, and that is a far better
  lever than any grant policy.
* **What does retail's server grant while the player click-walks?** Waypoint chains?
  The bare destination? At what cadence relative to the client's own progress?

**Why this is first:** every route below is a guess until this is answered, and this one
costs a script and no run. It is also the only route that can tell us the residual
no-clip is *unavoidable* rather than *unsolved*.

### R2 — WHICH gate fires? **One content row + one run**

`snaptest` (`0x006055E0`) has three gates and we have only ever confirmed **gate 1**
(separation, §1h.1). Gate 2 is a `MapFindPath` at range 300.0; **gate 3 is a step-
clearance predicate at `0x005FEF70`** — verified to be a real `push ebp` entry, so it
is one row in `content/movecode.toml` and a `gensites.py` regenerate, exactly like the
sites added for B3.

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
