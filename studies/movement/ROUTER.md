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
29 attributed live clicks across six captures (a METHOD-bounded count: the
op61-heading-vote cannot attribute a click-only session, and the one it
skips — connection 49545, zero op61 rows — holds 3 more clicks, each
answered with a bit-equal verbatim echo within 32 ms by click-echo
attribution; the excluded data confirms the contract, review 2026-08-26):

1. **First answer within one RTT** (observed 0.007–0.065 s): the verbatim
   clicked point when one leg suffices (16/29, every one bit-equal),
   otherwise a part-way FIRST waypoint (13/29).
2. **Further legs at leg-completion cadence at run speed** — grant(n+1)
   lands when the client completes leg n at 288 u/s (63805's eight legs
   through the committed pipeline: 277.8–325.9 u/s, six within ±4%).
3. **The terminal grant is the bit-exact clicked point** (every completed
   chain).
4. **Any new c2s input silently abandons the chain** — a re-click (5 by
   our assembly; the skeptic's census read one keyboard abort as
   click-caused, 6/1/1 — same 8 total), a keyboard resume (2), an op57
   interaction (1 — a single AMBIGUOUS specimen: a bit-identical re-grant
   lands 30 ms after the op57 and fits both "chain aborted, the interact's
   own route answered" and "chain continued, second leg never earned";
   n=1, labeled as such). "Unanswered" and "wins-late" were always this.
   Rotate/skill/attack opcodes never fired mid-chain in this corpus, so
   whether they abort is UNMEASURED (zero exposure — the L8 rule).

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
  own header staged it for the monster AI; this arc made it the first
  consumer (the monster AI remains the staged second).
- **`livewire.py`** (RETHINK #2) — the committed decode recipe the bench
  reads captures through, origin-gated to LIVE.
- The click handler's two "we cannot route" comments predated `route()`
  and were retired in place by the wiring build; the same staleness in
  pathmap.py's own header ("zero callers") and `route()`'s docstring
  ("SAME PLANE ONLY", written before `pair_id` was decoded) was caught by
  the review round and fixed. `studies/enemy/PLAN.md` still carries the
  expired premise ("the server cannot route") — noted there.

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
before this was found. The Q7 wrong-mesh trap, now code. (The review
explained the tie: content maps 146 and 148 share pathing file 113021 —
the same city's outpost and explorable — so the tie was structural, and
wire-first is still the right selector.)

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
  ~1.2km from ours at 0.34–0.41× our length; its observed fragment is
  clip-clean on our mesh. Superseded before revealing its full path.
  Two-legal-corridors tie-breaking, or a shorter corridor our mesh blocks
  further along — undecidable from the tape.
- **ROUTER-Q4** — retail grants shorter legs than corner-to-corner (grants
  at ~300–1000u spacing on straight stretches; a part-way first waypoint
  can sit ON the straight line, e.g. 1233.471's, 1.3u off ours). Mechanism
  unmeasured (leg cap? LOS budget?). Our router grants corner waypoints
  only; the client walks long straight legs happily (our own 766u leads),
  so this is cadence cosmetics, not legality. Not implemented; registered.
- **ROUTER-Q5** — no specimen clicks an unwalkable/off-mesh destination
  (all 29 dests are on-mesh; the GW client raycasts clicks onto ground).
  Retail's rule for such clicks is unmeasured.

### 3.1 The review round (2026-08-26, three adversarial lanes before merge)

**The bench's four headline claims were independently re-derived and ALL
REPRODUCED bit-for-bit** — own attribution, own chain assembly, own
point-to-polyline and D1 math, routerbench's functions run only afterwards
for comparison (row-for-row identical). The re-derivation is the
independence check the fidelity gate cannot be (the gate certifies
transcription of the skeptic's numbers; this lane re-earned them). Also
verified by adversarial rerun: swapping the dead-reckoned origin for the
raw last report degrades exactly the specimens §3 says it degrades.

Findings absorbed:

- **The sampling overclaim (wiring F1), FIXED in code**: "legal by
  construction" was legal at clip()'s 16 u sampling — a sub-sample sliver
  passes, sharpest on the clip-fallback. Every leg is now re-clipped at
  `A2_LEAD_CLIP_STEP` (2.0 u — the step Q7 itself calibrated) before
  anything goes on the wire, and the fallback's own clip runs at 2.0 u
  too; a route that survives 16 u but fails 2.0 is treated as no route.
  The bench's `legs_clean` likewise moved to step 2.0 (review F2: at the
  default step it re-ran route()'s own gate and could never fail).
- **The 13/13 is model-conditional for one specimen (bench F3)**: at a
  dead-reckon speed of 277 u/s (the low end of retail's own leg band) the
  62994@135.655 origin lands off-mesh and route() refuses; at ≥280 it is
  the bit-identical verbatim reproduction. 288 is the committed constant
  and the right one (the 63805 legs cluster on it), but the claim is
  "13/13 under the 288 u/s origin model," not model-free.
- **Two new composition refusals (wiring F2/F7)**: `--interact-walk`
  (0x002A straight-line order vs live chain — two movement orders for one
  body) and `--move-speed-effects` (chain ETAs assume 288; a snared
  client gets leg n+1 mid-leg and corner-cuts unvetted ground).
- **`--router --tape` prints a loud INERT notice** (wiring F5): under a
  tape no click can be routed; the banner now says so instead of printing
  predictions for a run that cannot exercise them.
- **ROUTER-Q9 (wiring F3), registered not fixed**: world_tick's unlocked
  `dest` read→clear can clobber a freshly granted leg's dest in a ~µs
  window per 50 ms tick; the router makes the two writers time-correlated
  (the chain grants at the exact ETA the integrator arrives). Worst case
  is model staleness on the terminal grant (pos frozen one waypoint
  short, report-silent). The identical window pre-exists at the shipped
  click fire; recorded with sizing rather than half-locked.
- The pre-batch owed-leg grant outruns an abandon in the same batch by at
  most the 0.05 s timeout floor (wiring F4) — comparable to retail's own
  one-RTT race; the bound comes from the floor, verified.
- `--cast-stop` composes and its click-walk suppression clause fires on
  every mid-chain cast (wiring F6) — conservative and warp-free, but its
  "no belief can place the body" justification is false under a chain
  (the dead-reckoning places it); folded into ROUTER-Q8's cast question.

## 4. ROUTER-B2 — the wiring (authsrv `--router`) — BUILT 2026-08-26, tests green

Opt-in flag, shipped default byte-identical. Under `--router`, the click
branch (0x003E) becomes:

1. Origin = `state["pos"]` (the 20 Hz integrator; B1's origin result).
   Clicks under active keyboard authority stay DROPPED (retail's own
   contract, §0.15 — rule 1 unchanged).
2. `route(origin → click)` on `state["pathmap"]`, then **every leg
   re-clipped at `A2_LEAD_CLIP_STEP` (2.0 u) before anything is sent**
   (the review's sampling gate — a route that survives route()'s own 16 u
   gate but fails 2.0 is treated as no route):
   - **Routed, one leg** → grant the verbatim click point (identical wire
     bytes to today's echo).
   - **Routed, multi-leg** → grant waypoint 1 now (speed row first, once);
     queue the rest with per-leg ETAs at 288 u/s; grant leg n+1 at leg n's
     completion; terminal grant is the exact click point.
   - **No route (or the re-clip demoted one)** → fall back to the ONE-LEG
     CLIP at the same 2.0 u step: grant its stop point if it moves the
     client by more than COLLISION_STEP and the origin is on-mesh, else
     refuse. This is NOT the tombstoned F-B clip (that replaced retail's
     echo for ALL geometry-flagged clicks; this fires only where no legal
     route exists — ROUTER-Q1's cross-component case — and its one grant
     is still a 2.0 u-sampled legal leg). A refusal is a `router_route`
     row with `verdict="refused"` and the reason named, never silent.
3. **Abandon on movement input**: any 0x003D, new 0x003E (new route), or
   0x0047 clears the chain (logged with cause). Interaction and cast
   opcodes do NOT abandon in v1 — that is ROUTER-Q8, not a shipped
   behavior (`--interact-walk` is refused in the composition matrix for
   exactly this reason).
4. **Planes**: per-waypoint `plane_first` via `plane_at(wp, prefer=carry)`
   with the carry as the refuse-to-guess fallback; `plane_second` is
   **matched to `plane_first`** via `a2_matched_field4` (§0.11's
   protection) — NOT retail's one-grant-lag half-zero pattern, a recorded
   deviation (ROUTER-Q7). The terminal grant's `plane_first` is the
   client's own click plane.
5. **Scheduler**: rides the recv loop — the 1.0 s timeout poll and the
   pre-batch flush site — with the socket timeout shortened to the next
   leg ETA (clamped to [0.05, 1.0]) only while a chain is live, so chain
   grants land at leg completion, not up to 1 s late. `policyreplay`'s
   `QUIET_TICK=1.0` stays correct for every log it gates (no old log has a
   chain).
6. **Observability** (instrument-#1 discipline): a `router_route` row per
   click carrying the verdict plus the fields that verdict earns (routed
   and refused rows carry origin + compute ms; verbatim carries dest + ms;
   kbd-drop carries the keyboard age), and `router_leg` rows per
   grant/abandon with cause, the terminal grant marked.
7. Under `--router`, a click never arms `grant_pending` and never consults
   the rate floor — retail answers every click within one RTT (29/29), and
   the hold/void/freshness tower exists to police a regime the router no
   longer enters. The keyboard channel (D1 leads, clip, watchdog) is
   untouched; `--router` composes with `--d1-lead`.

Build notes beyond the spec above, all tested (`test_router.py`, floor 51;
`test_d1lead.py` floor 86 with its three source-census locks updated to
name the router's new call sites; `test_grantsim.py` 86, `test_policyreplay.py`
14, `test_srclint.py` 22 all green):

- The keyboard drop reads Rule 1's latch **directly** (same arithmetic,
  negative age counts as armed) rather than through `_grant_verdict` — the
  drop is retail's measured contract and must not evaporate under
  `--no-grant-suppress`.
- The scheduler grants **one leg per tick even when late**: the client has
  been parked at the current waypoint since the leg completed (it cannot
  walk a leg nobody granted), so cadence restarts at the grant instant.
  The first draft of the test asserted queue-draining and the reasoning
  above refuted it — recorded because the wrong version looks efficient.
- The recv socket timeout shrinks to the next leg ETA (clamped
  [0.05, 1.0] s) only while a chain is live; `policyreplay.QUIET_TICK=1.0`
  stays true for every log its gate rules on (no old log holds a chain).
- Plane pairs are **matched everywhere with one named carve-out**
  (`a2_matched_field4`, §0.11's own protection): the one-leg verbatim
  answer matches field 4 only under `--d1-lead`, because it promises wire
  bytes identical to the shipped echo and the shipped echo is
  D1-conditional there — without the flag it sends the client's raw
  `(dest_plane, cur_plane)`, exactly as the echo does. Interior field-3 is
  `plane_at(wp, prefer=carry)` with the carry as the refuse-to-guess
  fallback, the terminal field-3 is the client's own click plane.
  ROUTER-Q7 records the deviation from retail's half-zero lag pairs.
- Composition: refused with the seven probe/diagnostic arms
  (`click-sweep`, `arrival-carry`, `cancel-answer`, `stop-answer`,
  `family-rate-probe`, `checksum-probe`, `pc-spoof`); composes with
  `--d1-lead` (the live-run bundle) and both `--grant-suppress` states.
- New open items: **ROUTER-Q6** — no origin-snap in v1: a wall-pressed
  origin that penetrates the mesh (P-17 observed ~0.25 u) refuses with
  `origin-off-mesh` logged rather than snapping to the nearest trapezoid;
  build the snap only if the owner run shows the refusal firing on real
  play. **ROUTER-Q7** — matched plane pairs vs retail's one-grant-lag
  half-zero pairs (above). **ROUTER-Q8** — only 0x003D/0x003E/0x0047
  abandon a chain; retail also aborted on an op57 interaction (n=1,
  ambiguous — §1 clause 4), and our interaction/cast opcodes do not yet
  abandon. The cast path composes conservatively (cast-stop's click-walk
  suppression fires on every mid-chain cast — warp-free, but its stated
  justification is false under a chain, §3.1); `--interact-walk` is
  refused outright. **ROUTER-Q9** — the world-tick dest-clobber µs race,
  registered with sizing in §3.1.

## 5. ROUTER-P — pre-registered predictions for the owner's verification run

Registered 2026-08-26, before any live run under `--router` (the flag's
startup banner prints the same list). The run protocol is the P-17 script
plus ordinary play: free clicks, mid-route re-clicks, the wall press with
clicks, a cross-floor click, keyboard interleave.

- **ROUTER-P1 — zero wall/prop phasing on click routes.** Every granted
  leg is clip-clean at the 2.0 u sampling step before it is sent; movetap
  shows no body passing geometry on a click answer. REFUTED IF a
  2.0 u-clean granted leg still phases — score the SAMPLER first (a
  sub-2 u sliver is our resolution limit, not the mesh being wrong), and
  only then mesh-vs-client walkability divergence, which is campaign-level
  news scored against the mesh, not the router.
- **ROUTER-P2 — the cross-floor click** (the 143431 warp case) **routes
  legally or refuses with the reason logged.** No straight-line
  cross-floor grant exists in the log. REFUTED IF a `router_route` row
  shows verbatim/clip-fallback across planes where route() should have
  cornered.
- **ROUTER-P3 — chains walk without rubber-banding**, grants landing at
  leg completion (movetap dir/point continuous through waypoints; no
  0x002C resync storm). REFUTED IF the client visibly snaps at leg
  boundaries — the cadence model or the parked-client model is wrong.
- **ROUTER-P4 — the P-17 wall-press cell yields only refusals or legal
  routes.** `lead_clip_why`-class visibility: every wall-press click
  produces a `router_route` row reading `refused (origin-off-mesh)` or a
  routed answer whose legs are legal; the unclipped pass-through door no
  longer exists on the click channel. REFUTED IF any wall-press click
  produces a grant whose leg crosses the boundary.
- **Exposure floors**: ≥10 free clicks, ≥3 mid-route re-clicks, ≥3
  wall-press clicks, ≥1 cross-floor click, else the affected cell is
  VOID, not a null (the L8 rule).

## 6. The verification run — 20260826T192724, scored (OBSERVED)

The owner played the Isle (map 280) under `--d1-lead --router`: 233 s,
254 clicks, drag-steering heavy. Tape `movetap-20260826T192742` scored
against the 280 mesh (91.2% of samples on-mesh). Owner's report: "still
warping."

**Map authority trap, caught mid-scoring**: the client's game version
header carries the character's SAVED map (148 here), not the loaded one —
the first scoring pass ran against Pre-Searing's mesh (23% coverage)
before the server's own `MAP_UPDATE_CURRENT` send (0x0118 = 280) and the
spawn coordinates settled it. On OUR captures the map authority is the
server's send; the wire-first rule for LIVE captures (op409) is
unaffected.

**The router held.** 24 clicks answered (12 routed chains at n_wp 2–4 and
0.9–14.7 ms compute, 10 verbatim, 2 clip-fallbacks on clicks at
unwalkable spots), 230 dropped under keyboard authority — the 6–7 Hz
click-trains with smoothly curving destinations are DRAG movement, which
emits 0x003E streams alongside 0x003D; the drops are retail's own
contract. Zero teleports on the tape (max per-sample step 44.9 u, run
speed), zero wall-crossings between on-mesh samples, zero watchdog fires,
three chains abandoned by re-click. **P-1: one blemish** — a 0.3 s /
5-sample off-mesh graze mid-leg on one chain (the body's own line runs
beside our clipped leg line — mesh-edge class, ~86 u of travel).
**P-3: pass** (no rubber-band signal). **P-4: pass as drops** — the
wall-press clicks arrived under keyboard authority and were dropped; no
unclipped pass-through exists on the click path. **P-2: VOID** — no
cross-floor click identified (that cell's exposure floor unmet).

**The remaining warp engine was the KEYBOARD channel, and it is what the
owner saw**: 99 fired D1 leads — 61 clipped, 19 clear, and **19 through
`a2_clip_lead`'s origin-unwalkable door as full unclipped 766 u rays**.
Eleven of the tape's twelve off-mesh episodes (~21 s total, longest
9.6 s) begin on exactly those grants, all during drags, where the
reported position rides our mesh edge. The router had closed this door's
twin on the click channel; the keyboard channel still had it open —
P-17(a), by the other road.

**ROUTER-B3 — the door closed** (same commit as §6): an
off-mesh origin now receives a ZERO-DISTANCE lead — the granted point is
the report itself, the shipped zero-lead answer shape for that row — so
no walk is ever ordered from ground our mesh cannot place, and the
client stays authoritative exactly where our decode has nothing to say
(which is also what the long `clipped`-grant episodes want: the client
walking real ground our mesh lacks now gets no orders fighting it).
One-line change in `a2_clip_lead`; the test cell that used to PIN the
door open now pins it closed, with the run's 19/99 as the why.
**Re-run prediction, registered**: the drag-phase off-mesh episodes lose
their 766 u ray injections — a phasing episode that still occurs under
free drag input is then a pure mesh-fidelity residual (client-vs-decode
edge disagreement), not a server-ordered walk. REFUTED IF a post-B3 tape
shows an off-mesh episode beginning at a fired lead whose row says
origin-unwalkable.

## 7. Run 2 — 20260826T194505, scored, and ROUTER-B4 (OBSERVED)

**B3's registered prediction HELD**: 68 fired keyboard leads, the 14
`origin-unwalkable` rows now zero-distance demotions; the tape's off-mesh
episodes collapsed from a 9.6 s worst case to ≤3.5 s (14 short episodes,
all in one drag phase — the predicted mesh-edge residual). Wall-press
clicks "seem stable now" per the owner. Zero teleports again (whole-run
census, >600 u/s cut).

**What the owner reported next, decoded from the rows:**

- *"Third click did atrocious pathing all the way around to terrain below
  a prop"* — the t=49.257 click: a 1,020 u click answered with a
  **twelve-waypoint ~12,000 u island tour** (46 s of walking, corridor
  passing planes 20 and 23). *"All of them bugged around corners / stupid
  paths"* and *"walking under stairs / pathing to terrain under props"* —
  endpoint selection took `containing()[0]` blind on stacked geometry
  (the review's F9 "fidelity nit", promoted by this run), and grant plane
  words came from per-point `plane_at` re-guesses.
- *"The cross-floor click warped me back"* — t=311.099: a 560 u click
  answered by a 5-leg ~4,300 u loop that crossed a plane-29 ramp,
  **overshot the destination by 900 u and walked back** (the tape shows
  continuous 288 u/s walking, no snap — the "warp" is the route's shape,
  not a teleport).
- *Mid-route re-clicks fine except elevation* — consistent: the defect
  class is stacked-plane endpoint selection, exactly where elevation is.

**ROUTER-B4 — plane-aware routing + the tour cap** (same commit):

1. `pathmap.route()` gains `start_plane`/`goal_plane` (prefer semantics —
   an unmatched preference falls back rather than refusing) and
   `with_planes=True`, returning the corridor's own per-waypoint planes
   from the A*'s trapezoid chain. test_pathmap §11 proves preference
   selects each surface of a real stacked point ((-6854,13008), planes
   {0,36}) and that the plain call's paths are untouched (floor 65).
2. The wiring passes `cur_plane`/`dest_plane`, and chain grants carry
   **corridor-true planes** instead of `plane_at` guesses (terminal keeps
   the client's named click plane — the shipped stairs doctrine).
3. **The tour cap**: a route longer than `4.0 × direct + 800 u` is
   refused as a route (both run-2 specimens trip it at 11.8× and 7.7×;
   the largest bench-legitimate ratio is 2.93×; the SLACK term protects
   short-range cornering) and demotes to the clip-fallback — walk
   straight toward the click, stop at the geometry, which is what the
   owner expected at both specimens. Constants measured-bounded, named
   `ROUTER_TOUR_CAP`/`ROUTER_TOUR_SLACK`.

**Registered for run 3**: the island tours are gone (no `router_route`
row with a route length over the cap fires as routed); stacked-geometry
clicks resolve to the clicked surface (no more terrain-under-prop
terminals when the click named the prop's plane); cross-floor clicks
either route sanely (≤4×+800 u) or stop at the geometry. REFUTED IF a
tour-shaped chain still fires, or a click whose plane our mesh carries
at the dest still terminates on the other stack level. Open: the
route-shape quality inside the cap (corner-hugging wide swings from
edge-midpoint waypoints) is unaddressed — ROUTER-Q10 if the owner still
sees it.

## 8. Run 3 — 20260826T205658: the refusal lock-in, and ROUTER-B5 (OBSERVED)

Tour cap and plane-awareness held (zero routed rows ≥8 waypoints, 2
tour-caps fired, zero teleports on the tape a third time). The owner's
report — "weird at first, middle went fine with long far clicks over
props/stairs, warped when I eventually hit W" — decodes to a NEW
mechanism, and the owner's own hypothesis ("maybe the server wasn't
actually tracking my movement") is exactly right:

- At t≈97 the client stopped at (-4896.4, 1324.6) beside a plane-44
  structure — **8.0 u outside our mesh decode** (nearest walkable 8 u).
  The stop report was accepted; `state["pos"]` froze there.
- **Every one of the next 85 clicks was refused `origin-off-mesh`** —
  218 seconds of server silence. The client self-pathed all of them
  (CANCELWALK-B1's own finding — the client paths clicks regardless),
  walking ~4 km across the map; the click coordinates trace the whole
  journey. That was the "middle going fine": pure client-side pathing
  over props and stairs, with the server mute.
- With zero grants, the client's server-fed copy stayed parked the
  whole time. The first keyboard press ended it in the client's OWN
  consecutive reports: **(-7772, -127) at t=314.582, then (-4934, 1286)
  at t=314.837 — a 3.2 km self-snap back onto the parked copy.** The
  warp, in the client's handwriting; nothing the server sent moved
  anybody.

**The lesson, stated for the record: a refusal is not safe-by-inaction.
Mute long enough and the client's reconcile does the warping for us.**
The refusal path exists for holes we truly cannot cover, not for the
edge-penetrated stands players actually produce (0.25 u at P-17's wall,
8.0 u here).

**ROUTER-B5** (same commit): `pathmap.nearest_walkable(x, y, radius)` —
per-candidate clamp with every returned point verified `walkable()` —
and the wiring snaps an off-mesh routing origin to the nearest covered
point within `ROUTER_ORIGIN_SNAP` (16 u = COLLISION_STEP, twice the
worst observed penetration) before routing; the `snapped` distance rides
every `router_route` row. A stand deeper than the radius still refuses —
and refusals now count a **streak** (on every row, with a console
warning every 10) so a lock-in can never again be silent. test_pathmap
§12 (floor 69) proves a real 12 u penetration returns to a walkable
point 0.12 u off the edge; test_router (floor 68) proves the 8 u
run-3 stand is now ANSWERED verbatim and the streak counts on true
holes. **ROUTER-Q11**: stands deeper than 16 u over true decode holes
(e.g. ON an undecoded structure) still refuse and still build the
divergence; the streak warning is the tripwire, a resync-class answer
is the unbuilt candidate if the owner's maps hit it.

**Registered for run 4**: no origin-off-mesh refusal streak reaches 10
on ordinary ground (the snap absorbs edge penetrations); wall-press and
prop-adjacent stands get answered clicks; the W-press reconcile snap
does not recur absent a streak. REFUTED IF a streak ≥10 occurs at a
stand within 16 u of our mesh (the snap failed its own case), or a
kilometre-class self-snap appears in the client's reports without a
preceding refusal streak (the divergence has another engine).
