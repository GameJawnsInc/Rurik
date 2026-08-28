"""Retail's click->chain contract as a committed census, and pathmap.route()
scored against it.

ROUTER-B1 (studies/movement/ROUTER.md; RETHINK-H3, owner-ordered 2026-08-26).
This module commits the RETHINK-QB analysis layer that measured retail's click
answer as A PATHFINDER'S OUTPUT -- the layer the mistakes review's class 8
warned about: every number REALFIX.md sec.0.19 quotes (29/29 within one RTT,
16 verbatim / 13 part-way first waypoints, leg-completion cadence at run
speed, bit-exact terminal grants, chain supersession on new input) was
computed by scratchpad scripts whose sys.path named a worktree that no longer
exists. The decode recipe was committed as livewire.py the same night; the
attribution, matching, chain-assembly and cadence math on top of it were not.
They are now, here.

THE FIDELITY GATE (same discipline as policyreplay.py): before this bench's
scoring of OUR router is quotable, census() must reproduce the desk-skeptic's
committed numbers from the same tapes -- the click count, the within-one-RTT
count, the 16/13 verbatim/part-way split, the 63805 chain's nine grants with
monotone along-fraction and a bit-exact terminal. A bench that cannot
reproduce the numbers it was built from has no standing to score a router.
test_routerbench.py holds that gate and a synthetic bare-machine section.

WHAT SECTION B MEASURES (score_specimen): for each retail click, run OUR
pathmap.route() from the same origin to the same destination and report --
routed-or-refused (with the reason attributed via containing()/components),
our first waypoint vs retail's first grant, chain length vs retail's, whether
retail's own legs are clip-clean on OUR mesh (the Q7 question, continued),
and terminal exactness. These are MEASUREMENTS of two different pathfinders
over (approximately) the same geometry, not pass/fail: different tie-breaking
gives different-but-equally-legal routes, so proximity is reported and never
gated. The hard invariants (every routed leg clip-clean, terminal == click
point when routed) are route()'s own contract and ARE gated in the test.

MESH SELECTION (the Q7 wrong-mesh trap, as code): the wire names its own map
-- s2c opcode 409's third field carries the map id at instance load (OBSERVED
2026-08-26: 409=[409,1,146,...] on the character C connection, [409,1,280,...]
on the Isle specimen), so selection is wire-first: resolve that id through
content's map rows to a pathing file id. The coverage census over the
connection's own reported positions is then a VERIFICATION, not a selector --
a connection whose wire-named mesh cannot contain MESH_COVERAGE_FLOOR of its
own reported positions is refused, never scored against a guess. (The census
alone proved insufficient the first time this ran: two candidate meshes both
scored 1.00 on one connection and the tie broke lexically.) Scoring retail
geometry against a mesh the wire did not name is how Q7's first pass produced
a 362u median error against the wrong map.

ORIGIN DISCIPLINE: everything here reads live captures through
livewire.live_captures(), which is origin-gated to LIVE and refuses to pool.

Usage:
    python toolkit/clientscan/routerbench.py --census
    python toolkit/clientscan/routerbench.py --score
    python toolkit/clientscan/routerbench.py --score --map 280
"""

import argparse
import math
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TOOLKIT, "authsrv"))
sys.path.insert(0, os.path.join(TOOLKIT, "mapdata"))
sys.path.insert(0, TOOLKIT)

import livewire                                                # noqa: E402
import pathmap as pathmapmod                                   # noqa: E402
import content                                                 # noqa: E402

# ---------------------------------------------------------------------------
# Measured constants. Each is a fact about the tapes or the skeptic's own
# method, not a tunable; the fidelity gate is what keeps them honest.
# ---------------------------------------------------------------------------
# First-answer window. Observed first-grant latencies on the 29-click corpus
# are 0.007-0.065s (desk-skeptic QB-4); 0.2s is the census cut the skeptic
# used, an order of magnitude of slack over the worst observed answer.
RTT_WINDOW = 0.2
# Attribution window for the op61-heading-vote (dsk_qb_02's method): a grant
# within this of a heading report votes for its agent as the player.
PROMPT_WINDOW = 0.15
# Terminal-finder tolerance: a grant within this of the click point ends the
# chain. Bit-exactness is then REPORTED separately (terminal_exact), never
# assumed from this tolerance. The nearest observed non-terminal offset is
# 131.1u (the smallest part-way first waypoint), so any cut in (0, 131)
# yields the same split; 5.0 is the skeptic's own value.
EXACT_TOL = 5.0
# The reference run speed. agents.agent_update_speed: 1.0 == 288 u/s;
# retail's own chain legs measured 277-328 u/s, six of eight within 4%.
RUN_SPEED = 288.0
# A connection is scored only against a mesh whose coverage of the
# connection's own reported positions clears this floor (Q7's census: the
# right mesh scored 0.72, the wrong one 0.56).
MESH_COVERAGE_FLOOR = 0.60

# Decoded opcodes (decimal, as tape.decode_all returns them).
OP_REPORT = 61    # c2s 0x003D [hdr, (x,y), plane, (dx,dy), movementType]
OP_CLICK = 62     # c2s 0x003E [hdr, (x,y), plane]
OP_STOP = 71      # c2s 0x0047 [hdr, (x,y), plane]
OP_GRANT = 41     # s2c 0x0029 [hdr, agent, (x,y), plane_first, plane_second]
OP_SPEED = 43     # s2c 0x002B [hdr, agent, fraction, mt]

# c2s opcodes that supersede a chain. The skeptic's abort census found three
# abort causes on the 8 never-completed chains: a later click (6), keyboard
# resume (1), an op57 interaction (1). Position pings and heartbeats are not
# input and do not abort.
# CAUTION, and it has now cost this arc three lanes: INPUT_OPS contains
# OP_REPORT and OP_STOP, i.e. BOTH position-bearing opcodes. Any exposure
# window CLOSED on INPUT_OPS and then searched for position rows inside it
# returns 0 IDENTICALLY, for any corpus -- the counted event is the
# terminator. Two independent lanes published that forced zero before it was
# caught, and a splice control recovered 0 of 27 synthetic reports with the
# exposure falling exactly 50.0%. See movecode/FINDINGS.md sec.1p.4 and
# sec.1s.7. For that question use a COMMAND-ONLY terminator ({OP_CLICK, 57},
# optionally OP_STOP) -- never this set.
INPUT_OPS = frozenset({OP_REPORT, OP_CLICK, OP_STOP, 57})

# s2c instance-load row; its third field is the map id (see MESH SELECTION
# in the module docstring).
OP_INSTANCE = 409


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# ---------------------------------------------------------------------------
# Stream readers (over livewire.decode_conn's merged rows)
# ---------------------------------------------------------------------------

def player_agent(merged):
    """(agent_id, votes) via the op61-heading-vote, or (None, Counter()).

    dsk_qb_02's method, committed: for every c2s heading report, the first
    s2c grant within PROMPT_WINDOW votes for its agent. The player's agent
    wins by landslide on every attributable connection (505-vs-1 on 63805,
    89-vs-4 on 62994 -- desk-skeptic, corroborated by an independent
    grant-to-track-distance method).
    """
    headings = [t for t, d, op, _v in merged if d == "c2s" and op == OP_REPORT]
    grants = [(t, v[1]) for t, d, op, v in merged
              if d == "s2c" and op == OP_GRANT]
    votes = Counter()
    gi = 0
    for ht in headings:
        while gi < len(grants) and grants[gi][0] < ht:
            gi += 1
        j = gi
        while j < len(grants) and grants[j][0] <= ht + PROMPT_WINDOW:
            votes[grants[j][1]] += 1
            break
    if not votes:
        return None, votes
    return votes.most_common(1)[0][0], votes


def click_rows(merged):
    """[(t, (x, y), plane)] for every c2s click."""
    return [(t, tuple(v[1]), v[2]) for t, d, op, v in merged
            if d == "c2s" and op == OP_CLICK]


def grant_rows(merged, agent):
    """[(t, (x, y), plane_first, plane_second)] for one agent's grants."""
    return [(t, tuple(v[2]), v[3], v[4]) for t, d, op, v in merged
            if d == "s2c" and op == OP_GRANT and v[1] == agent]


def last_pos_before(merged, when):
    """((x, y), plane, age_s) from the last position-bearing c2s row < when.

    Only op61 (heading report) and op71 (stop) carry a reported position; a
    click is intent, not a position, and is never used here. None when the
    connection has no position row before `when` -- refused, not guessed.
    """
    best = None
    for t, d, op, v in merged:
        if t >= when:
            break
        if d == "c2s" and op in (OP_REPORT, OP_STOP):
            best = (tuple(v[1]), v[2], when - t)
    return best


def modeled_origin(merged, agent, when):
    """((x, y), age_s) -- the client's position at `when`, dead-reckoned.

    The client is markedly quieter -- NOT silent -- during click-walks
    (sec.0.18 as corrected 2026-08-28; the "zero counterexamples" figure was
    an artifact of a window whose terminator set was THIS MODULE's INPUT_OPS
    at :108, which contains OP_REPORT itself). Command-terminated: 24 reports
    inside K=27 windows / 79.73 s, of which 3 are at the odometer stride. So
    for a click issued mid-chain the last REPORT is USUALLY, not always, the
    start of the previous walk -- which is why this function returns age_s: so
    a caller can tell the two cases apart instead of assuming the stale one.
    Retail routes from the agent's
    actual position; this models it the way the contract itself was measured:
    from each grant the client order-walks toward the granted point at
    RUN_SPEED until it arrives or the next event moves it (QB's own cadence
    decode -- grant(n+1) lands at leg completion at run speed). A c2s
    position row resets the model to what the client itself reported.
    age_s is the time since the model was last anchored by a REPORT (0.0 =
    fresh report; large = long dead-reckoned).
    """
    pos = None
    walk = None          # (t_granted, from_pos, dest)
    anchored_at = None

    def at(t):
        if walk is None:
            return pos
        t0, frm, dst = walk
        leg = dist(frm, dst)
        if leg <= 0.0:
            return dst
        f = (t - t0) * RUN_SPEED / leg
        if f >= 1.0:
            return dst
        return (frm[0] + f * (dst[0] - frm[0]),
                frm[1] + f * (dst[1] - frm[1]))

    for t, d, op, v in merged:
        if t >= when:
            break
        if d == "c2s" and op in (OP_REPORT, OP_STOP):
            pos, walk, anchored_at = tuple(v[1]), None, t
        elif d == "s2c" and op == OP_GRANT and v[1] == agent:
            here = at(t)
            if here is not None:
                pos, walk = here, (t, here, tuple(v[2]))
    final = at(when)
    if final is None:
        return None
    return final, (when - anchored_at if anchored_at is not None else None)


def chain_for_click(merged, agent, click_t, click_pt):
    """The grants this click owns, and how the chain ended.

    Returns (grants, end) where grants is [(t, (x,y), pf, ps)] and end is
    "terminal" (a grant within EXACT_TOL of the click point arrived; it is
    the last element), "superseded:<op>" (a later c2s input row arrived
    first), or "open" (the capture ended mid-chain).

    Attribution rule (the skeptic's, after the first-pass join manufactured
    11 false chains): a chain is the player-agent grants strictly after the
    click and before the next c2s INPUT row; nothing after another input is
    ever this click's answer.
    """
    grants = []
    end = "open"
    next_input = None
    for t, d, op, _v in merged:
        if t <= click_t:
            continue
        if d == "c2s" and op in INPUT_OPS:
            next_input = (t, op)
            break
    for t, pt, pf, ps in grant_rows(merged, agent):
        if t <= click_t:
            continue
        if next_input is not None and t >= next_input[0]:
            end = f"superseded:{next_input[1]}"
            break
        grants.append((t, pt, pf, ps))
        if dist(pt, click_pt) <= EXACT_TOL:
            end = "terminal"
            break
    else:
        if next_input is not None:
            end = f"superseded:{next_input[1]}"
    return grants, end


def leg_speeds(origin, grants):
    """[(leg_len, dt, u_per_s)] for the observable legs of a chain.

    Leg n runs from waypoint n-1 (the origin for n=1) to waypoint n and is
    walked between grant n and grant n+1, so its speed is measurable only
    when grant n+1 exists. Verified against the 63805 chain by hand before
    this was committed: leg wp3->wp4 is 557u walked in 1.946s = 286 u/s.
    """
    out = []
    pts = [origin] + [g[1] for g in grants]
    for n in range(1, len(grants)):
        leg = dist(pts[n - 1], pts[n])
        dt = grants[n][0] - grants[n - 1][0]
        if dt > 0:
            out.append((leg, dt, leg / dt))
    return out


def along_fraction(origin, click_pt, pt):
    """pt's projection onto the origin->click ray, normalized (1.0 = click)."""
    vx, vy = click_pt[0] - origin[0], click_pt[1] - origin[1]
    d2 = vx * vx + vy * vy
    if d2 <= 0.0:
        return 0.0
    return ((pt[0] - origin[0]) * vx + (pt[1] - origin[1]) * vy) / d2


# ---------------------------------------------------------------------------
# Section A: the committed retail census (the fidelity gate's subject)
# ---------------------------------------------------------------------------

def census(root=None):
    """Every click in the LIVE corpus, classified.

    Returns (rows, skipped). Each row is a dict:
      cap, conn, t, click (x,y), agent,
      first_dt   -- latency of the first owned grant (None if none),
      first_dist -- that grant's distance to the click point,
      kind       -- "verbatim" | "part-way" | "no-answer",
      n_grants, end, origin ((x,y) or None), origin_age,
      terminal_exact -- True when the chain's last grant == click bit-exact.
    Connections that fail decode/attribution are in `skipped` with reasons,
    never silently dropped.
    """
    rows, skipped = [], []
    for capdir, gf in livewire.live_connections(root):
        cap = os.path.basename(capdir)
        try:
            _conn, merged, ok = livewire.decode_conn(capdir, gf)
        except Exception as e:                                  # noqa: BLE001
            skipped.append((cap, gf, f"decode-raised:{e!r}"))
            continue
        if not ok:
            skipped.append((cap, gf, "decode-not-ok"))
            continue
        clicks = click_rows(merged)
        if not clicks:
            continue
        agent, _votes = player_agent(merged)
        if agent is None:
            skipped.append((cap, gf, "no-player-attribution"))
            continue
        for ct, cpt, _cplane in clicks:
            grants, end = chain_for_click(merged, agent, ct, cpt)
            first = grants[0] if grants else None
            first_dt = None if first is None else first[0] - ct
            first_dist = None if first is None else dist(first[1], cpt)
            if first is None or first_dt > RTT_WINDOW:
                kind = "no-answer"
            elif first_dist <= EXACT_TOL:
                kind = "verbatim"
            else:
                kind = "part-way"
            pos = last_pos_before(merged, ct)
            terminal_exact = bool(
                grants and end == "terminal"
                and grants[-1][1] == (cpt[0], cpt[1]))
            rows.append({
                "cap": cap, "conn": gf, "t": ct, "click": cpt,
                "agent": agent, "first_dt": first_dt,
                "first_dist": first_dist, "kind": kind,
                "n_grants": len(grants), "end": end,
                "origin": None if pos is None else pos[0],
                "origin_age": None if pos is None else pos[2],
                "grants": grants,
                "merged_ref": None,
            })
    return rows, skipped


# ---------------------------------------------------------------------------
# Section B: route() vs retail, mesh-selected
# ---------------------------------------------------------------------------

def mesh_candidates():
    """{map_id: (name, file_id)} from the owner's own content rows."""
    world = content.load()
    out = {}
    for mid, row in world.tables.get("map", {}).items():
        fid = row.get("file_id")
        if fid:
            out[str(mid)] = (row.get("name", "?"), int(fid))
    return out


def connection_points(merged):
    """Every reported (x, y) on a connection (op61 + op71) -- the coverage
    census population. Clicks are excluded: they are intent, and clicking an
    unwalkable point must not count against a mesh."""
    return [tuple(v[1]) for t, d, op, v in merged
            if d == "c2s" and op in (OP_REPORT, OP_STOP)]


def wire_map_id(merged):
    """The map id the connection's own instance-load row names, or None."""
    for _t, d, op, v in merged:
        if d == "s2c" and op == OP_INSTANCE and len(v) > 2:
            return v[2]
    return None


# One PathingMap per file id per process: select_mesh runs per connection
# and the maps are immutable, so reloading them per call would re-parse the
# chunk (and rebuild the walkable() grid) for nothing.
_PM_CACHE = {}


def _load_pm(fid, archive=None):
    pm = _PM_CACHE.get(fid)
    if pm is None:
        pm = pathmapmod.PathingMap.load(fid, archive=archive)
        _PM_CACHE[fid] = pm
    return pm


def select_mesh(points, candidates=None, archive=None, floor=None):
    """(map_id, PathingMap, coverage, censuses) or (None, None, best, censuses).

    The Q7 rule as code: walk every candidate mesh, score the fraction of the
    connection's own reported positions it contains, take the argmax, and
    refuse (None) when even the winner is below the floor.
    """
    floor = MESH_COVERAGE_FLOOR if floor is None else floor
    candidates = candidates or mesh_candidates()
    censuses = {}
    best_id, best_pm, best_cov = None, None, -1.0
    if not points:
        return None, None, 0.0, censuses
    for mid, (_name, fid) in sorted(candidates.items()):
        try:
            pm = _load_pm(fid, archive=archive)
        except Exception as e:                                  # noqa: BLE001
            censuses[mid] = f"load-failed:{e!r}"
            continue
        hits = sum(1 for x, y in points if pm.walkable(x, y))
        cov = hits / len(points)
        censuses[mid] = cov
        if cov > best_cov:
            best_id, best_pm, best_cov = mid, pm, cov
    if best_cov < floor:
        return None, None, best_cov, censuses
    return best_id, best_pm, best_cov, censuses


def heading_clip_agreement(merged, agent, pm, step=2.0):
    """Does retail's keyboard-lead truncation land on THIS mesh's boundary?

    The strongest available mesh-identity check (Q7's, committed): a heading
    report answered by a D1 lead carries its own prediction -- dest =
    reported + vec2 + 0.5*unit(vec2), bit-exact on 3,532 pairs (REALFIX
    sec.0.9) -- so a grant SHORT of that prediction was truncated by retail's
    own geometry, and on the right mesh our clip() from the report toward the
    prediction stops within a few units of retail's stop (Q7: 248/701 <=3u on
    the census-selected mesh, near zero on the wrong one). Coverage cannot
    discriminate meshes that both contain every reported point; this can.

    Returns dict(n_pairs, n_exact, n_clipped, agree3, agree10, dists) where
    n_exact counts bit-band D1 answers (formula confirmed, mesh untested),
    and agree3/agree10 count clipped answers whose our-clip stop lies within
    3u/10u of retail's.
    """
    reports = [(t, tuple(v[1]), tuple(v[3]), v[4])
               for t, d, op, v in merged
               if d == "c2s" and op == OP_REPORT and v[4] != 0]
    grants = grant_rows(merged, agent)
    out = {"n_pairs": 0, "n_exact": 0, "n_clipped": 0,
           "agree3": 0, "agree10": 0, "dists": []}
    gi = 0
    for rt, pos, vec, _mt in reports:
        mag = math.hypot(vec[0], vec[1])
        if not 700.0 <= mag <= 769.0:
            continue
        while gi < len(grants) and grants[gi][0] < rt:
            gi += 1
        if gi >= len(grants) or grants[gi][0] > rt + PROMPT_WINDOW:
            continue
        gpt = grants[gi][1]
        exp = (pos[0] + vec[0] + 0.5 * vec[0] / mag,
               pos[1] + vec[1] + 0.5 * vec[1] / mag)
        out["n_pairs"] += 1
        if dist(gpt, exp) <= 1.0:
            out["n_exact"] += 1
            continue
        # short of the prediction: retail truncated. Where does OUR mesh
        # stop the same ray?
        out["n_clipped"] += 1
        stop = pm.clip(pos[0], pos[1], exp[0], exp[1], step=step)
        d = dist(stop, gpt)
        out["dists"].append(round(d, 2))
        if d <= 3.0:
            out["agree3"] += 1
        if d <= 10.0:
            out["agree10"] += 1
    return out


def _route_refusal_reason(pm, origin, dest):
    """Attribute a route() None: which precondition failed."""
    starts = pm.containing(origin[0], origin[1])
    if not starts:
        return "origin-off-mesh"
    goals = pm.containing(dest[0], dest[1])
    if not goals:
        return "dest-off-mesh"
    return "no-path-or-gate"


def _point_to_polyline(pt, pts):
    """Min distance from pt to the polyline through pts."""
    best = float("inf")
    for a, b in zip(pts, pts[1:]):
        ax, ay = a
        bx, by = b
        vx, vy = bx - ax, by - ay
        d2 = vx * vx + vy * vy
        if d2 <= 0.0:
            d = dist(pt, a)
        else:
            f = ((pt[0] - ax) * vx + (pt[1] - ay) * vy) / d2
            f = 0.0 if f < 0.0 else (1.0 if f > 1.0 else f)
            d = dist(pt, (ax + f * vx, ay + f * vy))
        if d < best:
            best = d
    return best


def score_specimen(pm, origin, click_pt, retail_grants):
    """Compare OUR route(origin->click) against retail's observed chain.

    Measurement, not verdict: proximity numbers are for the study doc to
    interpret. The hard router invariants asserted here are route()'s own
    contract: when it routes, its terminal is the exact click point and every
    leg passes clip() end to end.
    """
    out = {"routed": False, "reason": None, "ours": None,
           "n_wp_ours": 0, "n_wp_retail": len(retail_grants),
           "first_wp_dist": None, "terminal_is_click": None,
           "legs_clean": None, "retail_legs_clean": None,
           "retail_max_dist_to_ours": None,
           "len_ours": None, "len_retail": None}
    route = pm.route(origin[0], origin[1], click_pt[0], click_pt[1])
    if route is None:
        out["reason"] = _route_refusal_reason(pm, origin, click_pt)
        return out
    out["routed"] = True
    out["ours"] = route
    # route() waypoints exclude nothing: [origin, corners..., click].
    out["n_wp_ours"] = max(0, len(route) - 1)
    out["terminal_is_click"] = (route[-1] == (click_pt[0], click_pt[1]))
    # At step=2.0, NOT the default: route()'s own final gate already
    # requires the default-16u clip to pass, so re-running it here could
    # never fail (review F2 -- a check that cannot fail is not a check).
    # The 2.0 step is 8x finer than the gate, matches the wiring's own
    # pre-send re-clip, and can genuinely catch a sub-16u sliver route()
    # stepped over.
    out["legs_clean"] = all(
        pm.clip(a[0], a[1], b[0], b[1], step=2.0) == (b[0], b[1])
        for a, b in zip(route, route[1:]))
    out["len_ours"] = sum(dist(a, b) for a, b in zip(route, route[1:]))
    if retail_grants:
        first_retail = retail_grants[0][1]
        # our first waypoint after the origin
        ours_first = route[1] if len(route) > 1 else route[0]
        out["first_wp_dist"] = dist(ours_first, first_retail)
        retail_pts = [origin] + [g[1] for g in retail_grants]
        out["len_retail"] = sum(dist(a, b)
                                for a, b in zip(retail_pts, retail_pts[1:]))
        out["retail_max_dist_to_ours"] = max(
            _point_to_polyline(g[1], route) for g in retail_grants)
        out["retail_legs_clean"] = all(
            pm.clip(a[0], a[1], b[0], b[1]) == (b[0], b[1])
            for a, b in zip(retail_pts, retail_pts[1:]))
    return out


def score_corpus(rows_by_conn=None, root=None, map_id=None, floor=None):
    """Section B over the live corpus. Returns (scored, refused).

    scored: [(census_row, mesh_id, coverage, score_dict)] for every click on
    a connection whose mesh census cleared the floor. refused: [(cap, conn,
    why)] for connections that could not be scored -- no position rows, no
    mesh above the floor -- refused loudly, never guessed.
    """
    scored, refused = [], []
    candidates = mesh_candidates()
    for capdir, gf in livewire.live_connections(root):
        cap = os.path.basename(capdir)
        try:
            _conn, merged, ok = livewire.decode_conn(capdir, gf)
        except Exception as e:                                  # noqa: BLE001
            refused.append((cap, gf, f"decode-raised:{e!r}"))
            continue
        if not ok:
            refused.append((cap, gf, "decode-not-ok"))
            continue
        clicks = click_rows(merged)
        if not clicks:
            continue
        agent, _votes = player_agent(merged)
        if agent is None:
            refused.append((cap, gf, "no-player-attribution"))
            continue
        pts = connection_points(merged)
        mid = wire_map_id(merged)
        if mid is None:
            refused.append((cap, gf, "no-instance-row"))
            continue
        mid = str(mid)
        if map_id is not None and mid != str(map_id):
            continue
        cand = candidates.get(mid)
        if cand is None:
            refused.append((cap, gf, f"map-{mid}-not-in-content"))
            continue
        try:
            pm = _load_pm(cand[1])
        except Exception as e:                                  # noqa: BLE001
            refused.append((cap, gf, f"mesh-load-failed:{e!r}"))
            continue
        if pts:
            cov = sum(1 for x, y in pts if pm.walkable(x, y)) / len(pts)
        else:
            cov = 0.0
        if cov < MESH_COVERAGE_FLOOR:
            refused.append((cap, gf,
                            f"map-{mid}-coverage-{cov:.2f}-below-floor"))
            continue
        for ct, cpt, _cplane in clicks:
            org = modeled_origin(merged, agent, ct)
            if org is None:
                refused.append((cap, gf, f"click@{ct:.3f}:no-origin"))
                continue
            grants, end = chain_for_click(merged, agent, ct, cpt)
            row = {"cap": cap, "conn": gf, "t": ct, "click": cpt,
                   "origin": org[0],
                   "origin_age": -1.0 if org[1] is None else org[1],
                   "n_grants": len(grants), "end": end}
            row["score"] = score_specimen(pm, org[0], cpt, grants)
            scored.append((row, mid, cov))
    return scored, refused


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_census():
    rows, skipped = census()
    print(f"live clicks: {len(rows)}   skipped connections: {len(skipped)}")
    for r in rows:
        dt = "  --  " if r["first_dt"] is None else f"{r['first_dt']:6.3f}"
        fd = "    --" if r["first_dist"] is None else f"{r['first_dist']:6.1f}"
        print(f"  {r['cap']}/{r['conn'].split('-to-')[0][-6:]}"
              f" t={r['t']:9.3f} +{dt}s d={fd}u {r['kind']:9s}"
              f" grants={r['n_grants']} end={r['end']}")
    for cap, gf, why in skipped:
        print(f"  SKIP {cap}/{gf}: {why}")
    kinds = Counter(r["kind"] for r in rows)
    within = sum(1 for r in rows
                 if r["first_dt"] is not None and r["first_dt"] <= RTT_WINDOW)
    print(f"kinds: {dict(kinds)}   within {RTT_WINDOW}s: {within}/{len(rows)}")
    return 0


def _print_score(map_id=None):
    scored, refused = score_corpus(map_id=map_id)
    print(f"scored clicks: {len(scored)}   refused: {len(refused)}")
    for row, mid, cov in scored:
        s = row["score"]
        if s["routed"]:
            fw = ("--" if s["first_wp_dist"] is None
                  else f"{s['first_wp_dist']:7.1f}u")
            rmax = ("--" if s["retail_max_dist_to_ours"] is None
                    else f"{s['retail_max_dist_to_ours']:7.1f}u")
            lr = ("--" if not s["len_retail"] or not s["len_ours"]
                  else f"{s['len_ours'] / s['len_retail']:5.2f}")
            print(f"  {row['cap']}/{row['conn'].split('-to-')[0][-6:]}"
                  f" t={row['t']:9.3f} map={mid}({cov:.2f})"
                  f" ours={s['n_wp_ours']:2d}wp retail={s['n_wp_retail']:2d}"
                  f" firstwp={fw} retail->ours max={rmax} len r={lr}"
                  f" age={row['origin_age']:5.1f}s"
                  f" clean={s['legs_clean']} retail_clean="
                  f"{s['retail_legs_clean']}")
        else:
            print(f"  {row['cap']}/{row['conn'].split('-to-')[0][-6:]}"
                  f" t={row['t']:9.3f} map={mid}({cov:.2f})"
                  f" REFUSED: {s['reason']}")
    for cap, gf, why in refused:
        print(f"  NOSCORE {cap}/{gf}: {why}")
    return 0


def _print_meshcheck():
    candidates = mesh_candidates()
    for capdir, gf in livewire.live_connections():
        cap = os.path.basename(capdir)
        try:
            _conn, merged, ok = livewire.decode_conn(capdir, gf)
        except Exception as e:                                  # noqa: BLE001
            print(f"  {cap}/{gf}: decode-raised:{e!r}")
            continue
        if not ok:
            continue
        agent, _votes = player_agent(merged)
        mid = wire_map_id(merged)
        if agent is None or mid is None:
            continue
        cand = candidates.get(str(mid))
        if cand is None:
            print(f"  {cap}/{gf.split('-to-')[0][-6:]}: map {mid} "
                  f"not in content -- unverifiable")
            continue
        pm = _load_pm(cand[1])
        r = heading_clip_agreement(merged, agent, pm)
        if r["n_pairs"] == 0:
            continue
        print(f"  {cap}/{gf.split('-to-')[0][-6:]} map={mid}: "
              f"pairs={r['n_pairs']} exact-D1={r['n_exact']} "
              f"clipped={r['n_clipped']} agree<=3u={r['agree3']} "
              f"<=10u={r['agree10']}")
    return 0


def _main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--census", action="store_true",
                    help="section A: the retail click census")
    ap.add_argument("--score", action="store_true",
                    help="section B: route() vs retail, mesh-selected")
    ap.add_argument("--meshcheck", action="store_true",
                    help="heading-clip mesh-identity check per connection")
    ap.add_argument("--map", help="restrict mesh candidates to one map id")
    args = ap.parse_args()
    if args.census:
        return _print_census()
    if args.score:
        return _print_score(map_id=args.map)
    if args.meshcheck:
        return _print_meshcheck()
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
