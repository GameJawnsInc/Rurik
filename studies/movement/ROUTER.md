# ROUTER — the retail-faithful click policy (RETHINK-H3, owner-ordered 2026-08-26)

The owner's ruling on RETHINK.md: **build the router.** This document is the
arc's record — the measured spec it implements, the bench that scores it, and
the wiring. Confidence labels per `studies/character/FINDINGS.md`.

**Identifiers.** `ROUTER-B<n>` = builds of this arc; `ROUTER-Q<n>` = open
questions it registers; `ROUTER-P<n>` = pre-registered predictions for the
verification run.

---

## 1. The spec (OBSERVED; REALFIX §0.19 / RETHINK-H2, desk-skeptic-confirmed)

Retail's click answer is a pathfinder's output. The measured contract, over
29 live clicks across six captures:

1. **First answer within one RTT** (observed 0.007–0.065 s): the verbatim
   clicked point when one leg suffices (16/29), otherwise a part-way FIRST
   waypoint (13/29).
2. **Further legs at leg-completion cadence at run speed** — grant(n+1)
   lands when the client completes leg n at 288 u/s (63805's eight legs:
   277–328 u/s, six within ±4%).
3. **The terminal grant is the bit-exact clicked point** (every completed
   chain).
4. **Any new c2s input silently abandons the chain** — a re-click (6), a
   keyboard resume (2 by our assembly; the skeptic's abort census read one
   of those as click-caused — same 8 total), an op57 interaction (1).
   "Unanswered" and "wins-late" were always this.

Wire grammar (OBSERVED from the 63805 specimen, probe 2026-08-26): a chain
is **one op43 speed row (1.0) at chain start**, then bare op41 grants —
retail does not resend the speed per leg, unlike our send site. Each grant
carries `[41, agent, (x,y), plane_first, plane_second]` with a per-waypoint
`plane_first` and `plane_second` trailing it by one grant — the plane-carry
one-grant-lag model, confirmed on retail's own chain. Interior waypoints are
integer-valued mesh vertices (four are bit-exact prop outline vertices in
our own archive decode — props #392/#396, map 280); the last corner before
the goal can be a computed edge point (−5824.36, 6430.0).

Composed with §0.18's regime measurement: retail grants only legal legs
into the order-walk regime, so the regime is harmless there. The D2 clip is
this router's zero-corner approximation; the verbatim echo its one-leg case.

## 2. The substrate (all pre-existing, none built for this arc)

- **`pathmap.route()`** (`toolkit/mapdata/pathmap.py:578`) — A* over the
  file's own stored trapezoid adjacency (symmetric, opposite-edge-consistent
  14,950/14,950) plus derived cross-plane portal links, string-pull
  smoothing, and a final per-segment `clip()` gate that returns `None`
  rather than a path through a wall. MEASURED p50 0.185 ms / max 16.6 ms on
  the biggest mesh. Zero production callers before this arc — the module's
  own header stages it for exactly this consumer.
- **`livewire.py`** (RETHINK #2) — the committed decode recipe the bench
  reads captures through, origin-gated to LIVE.
- The click handler's own comments ("we cannot route", authsrv.py ~15730,
  ~15765) predate `route()` and are stale; the wiring build retires them.

## 3. ROUTER-B1 — the bench (`toolkit/clientscan/routerbench.py`), BUILT, green

Commits the RETHINK-QB analysis layer (mistakes-review class 8: it lived in
a scratchpad hardcoded to a deleted worktree — literally non-runnable one
session later). `test_routerbench.py`, floor 48.

**Fidelity gate — PASSED on first run**: census() reproduces the committed
numbers from the same tapes: 29 clicks, 29/29 within one RTT, 16 verbatim /
13 part-way (identical offsets, 131.1u minimum), 8 superseded, the 63805
nine-grant monotone bit-exact-terminal chain.

**Mesh-identity check (`--meshcheck`), two independent reproductions**: a
D1-band heading answer short of its own bit-exact prediction was truncated
by retail's geometry, so our clip of the same ray tests mesh identity
directly — Q7's method, committed. Map 280 aggregate: **231/647 clipped
stops agree ≤3u (35.7%)** — Q7's 248/701 (35.4%) reproduced by an
independent implementation. Map 146 (character C-area, wire-named):
**24/33 (73%)** — content's 146 mesh is the right mesh. The D1 formula's
bit-band rate reproduces everywhere (e.g. 185/195 on one connection).
Anchor locks in the test: 63805 (506 pairs / 297 exact / 209 clipped / 65
≤3u), 62994 (98/89/9/8).

**Mesh selection is wire-first**: s2c op409's third field names the map at
instance load (OBSERVED: 146, 280, 148 across the corpus); the coverage
census is a verification with a 0.60 floor, not a selector — two candidate
meshes both scored 1.00 on one connection and the tie broke lexically
before this was found. The Q7 wrong-mesh trap, now code.

**Section B — `route()` vs retail's 29 answers** (26 scored; 3 on maps not
in content, 1 connection unattributable):

- **All 13 scoreable retail-verbatim clicks reproduce bit-identically**:
  our route is one leg, first-waypoint distance 0.0, length ratio 1.00.
  The one-leg special case is CONFIRMED on our own mesh.
- **Chained specimens run the same corridors**: 63805 — our 4 corners vs
  retail's 9 grants, every retail waypoint ≤120.3u from our polyline,
  length ratio 1.18; the Pre-Searing chain — ≤12.0u, ratio 1.26. Retail
  emits more, shorter legs (ROUTER-Q4); ours string-pulls to corners only.
- **The origin must be dead-reckoned** (registered prediction, held): the
  client is report-silent during click-walks, so a mid-chain click's last
  REPORT is seconds stale. Modeling the origin by walking granted legs at
  288 u/s (reset on any report) collapsed the worst mismatches — two
  specimens went from 3-corner detours with `retail_clean=False` to exact
  one-leg verbatim reproductions, and 24/26 specimens' observed retail legs
  are clip-clean on our meshes. **Wiring consequence: the router routes
  from `state["pos"]` (authsrv's world-tick integrator — the same model),
  never from the last raw report.**

**Open specimens registered, not smoothed over:**

- **ROUTER-Q1** — 60935 t=58.694 (map 148): `route()` refuses
  (no-path-or-gate) where retail answered a 131.1u part-way waypoint.
  Pre-Searing's mesh fragments into 15 components (largest 78%); a
  cross-component click is unroutable on our decode. The wiring's fallback
  (below) covers it.
- **ROUTER-Q2** — 52318 t=262.438 (map 280): retail's observed leg fails
  our clip and our route detours 9 corners; fresh origin, so not a
  staleness artifact. One specimen; prop-class remainder candidate.
- **ROUTER-Q3** — 62994 t=146.434/148.319 (map 146): retail's corridor runs
  ~1.2km from ours at 0.35–0.4× our length; its observed fragment is
  clip-clean on our mesh. Superseded before revealing its full path.
  Two-legal-corridors tie-breaking, or a shorter corridor our mesh blocks
  further along — undecidable from the tape.
- **ROUTER-Q4** — retail grants shorter legs than corner-to-corner (grants
  at ~300–1000u spacing on straight stretches; a part-way first waypoint
  can sit ON the straight line, e.g. 1233.471's, 3.1u off ours). Mechanism
  unmeasured (leg cap? LOS budget?). Our router grants corner waypoints
  only; the client walks long straight legs happily (our own 766u leads),
  so this is cadence cosmetics, not legality. Not implemented; registered.
- **ROUTER-Q5** — no specimen clicks an unwalkable/off-mesh destination
  (all 29 dests are on-mesh; the GW client raycasts clicks onto ground).
  Retail's rule for such clicks is unmeasured.

## 4. ROUTER-B2 — the wiring (authsrv `--router`) — spec

Opt-in flag, shipped default byte-identical. Under `--router`, the click
branch (0x003E) becomes:

1. Origin = `state["pos"]` (the 20 Hz integrator; B1's origin result).
   Clicks under active keyboard authority stay DROPPED (retail's own
   contract, §0.15 — rule 1 unchanged).
2. `route(origin → click)` on `state["pathmap"]`:
   - **Routed, one leg** → grant the verbatim click point (identical wire
     bytes to today's echo).
   - **Routed, multi-leg** → grant waypoint 1 now (speed row first, once);
     queue the rest with per-leg ETAs at 288 u/s; grant leg n+1 at leg n's
     completion; terminal grant is the exact click point.
   - **`route()` returns None** → fall back to the ONE-LEG CLIP: grant
     `clip(origin → click)`'s stop point if it moves the client, else
     refuse with a logged reason. This is NOT the tombstoned F-B clip (that
     replaced retail's echo for ALL geometry-flagged clicks; this fires
     only where no route exists — ROUTER-Q1's cross-component case — and
     every grant it emits is still a legal leg). A refusal is logged
     `router_refused`, never silent.
3. **Abandon on new input**: any 0x003D, new 0x003E (new route), 0x0047,
   or cancel-on-move interaction clears the chain (logged with cause).
4. **Planes**: per-waypoint `plane_first` via `plane_at(wp, prefer=carry)`;
   `plane_second` = previous grant's plane (the one-grant-lag model already
   in the codebase).
5. **Scheduler**: rides the recv loop — the 1.0 s timeout poll and the
   pre-batch flush site — with the socket timeout shortened to the next
   leg ETA (clamped to [0.05, 1.0]) only while a chain is live, so chain
   grants land at leg completion, not up to 1 s late. `policyreplay`'s
   `QUIET_TICK=1.0` stays correct for every log it gates (no old log has a
   chain).
6. **Observability** (instrument-#1 discipline): `router_route` per click
   (origin, dest, waypoint count, verdict, compute ms), `router_leg` per
   grant/abandon/done with cause.
7. Under `--router`, a click never arms `grant_pending` and never consults
   the rate floor — retail answers every click within one RTT (29/29), and
   the hold/void/freshness tower exists to police a regime the router no
   longer enters. The keyboard channel (D1 leads, clip, watchdog) is
   untouched; `--router` composes with `--d1-lead`.

## 5. ROUTER-P — pre-registered predictions (to fill at wiring landing,
before the owner's verification run)

(reserved)
