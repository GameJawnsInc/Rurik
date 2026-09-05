"""Walkable geometry: the navmesh a Guild Wars map carries in its pathing chunk.

This is what lets a server answer "is this point walkable" instead of letting a
character walk through walls. The client already refuses to render you through a
wall; without this the server disagrees with it and drags you back or shoves you
through.

WHERE THE LAYOUT COMES FROM. The struct names below are GuildWarsMapBrowser's
ImHex pattern (FFNA_ImHexPatterns/gw_file_pattern_complete.hexpat), Copyright (c)
2023 Jonathan Bjorn Greve, https://github.com/Jonathan-Greve/GuildWarsMapBrowser,
used under its licence -- terms and the credit that licence requires are in
THIRD-PARTY-NOTICES.md at the repository root, and this module is one of the two
it covers. That is ONE lineage -- the Jonathan-Greve and gwdevhub repositories
are a fork pair, so agreement between them is not corroboration -- and it has no
test or fixture. It is a hypothesis, not a spec.

WHAT MAKES IT EVIDENCE ANYWAY. The layout is self-checking, and it checks out:

  * The plane walk consumes tag 8 to the exact byte. Kamadan's tag 8 is 193,629
    bytes and 39 planes of ten sub-records land on 193,629 with nothing left
    over. Every element size participates -- a wrong 44 for the trapezoid, or 16
    for an x-node, or 9 for a portal, desyncs inside the first plane and lands
    the next tag byte on garbage.
  * Every sub-record's length equals its count from the plane header, and that
    count came from a different part of the file than the data it sizes.
  * All 1,270 of Kamadan's trapezoids are geometrically well formed: none has
    yTop below yBottom, none has a left x above its right x. A misread layout
    produces inversions in bulk, not zero.
  * The spawn point our server already used -- from OpenTyria's static config,
    never checked against anything -- falls inside exactly one trapezoid. One,
    not zero and not several, is what a non-overlapping tiling should give.

WHERE THE SOURCE IS WRONG. Tag 11's size field is exactly twice the length of
the data that follows, in all 39 of Kamadan's planes. The counts are
authoritative and the size field is not; anything that trusts it to skip forward
desyncs on every map. GuildWarsMapBrowser itself is unaffected because its
pattern indexes arrays by count and only displays the size.

THE ROUTING GRAPH WAS ALREADY IN THE PARSE. An earlier version of this file
said portals and the node blocks "are the pathfinding graph -- what you need to
route AROUND an obstacle", and skipped them. That was half wrong in a way worth
recording: the intra-plane graph is not in those blocks at all. It is the four
neighbour indices in every trapezoid record, which this file unpacked and threw
away on the next line.

  * MEASURED: 2,472 directed links in Kamadan and 12,478 in Pre-Searing, none
    out of range, and **every one symmetric** -- if A names B, B names A. On the
    stronger test that upstream's TL/TR/BL/BR naming predicts, a link across a
    top edge is answered across a bottom edge, 14,950 of 14,950. Nothing in our
    decoder forces that: the four indices in one 44-byte record are checked
    against four indices in a different record.

Portals (tag 9) carry the CROSS-plane structure and are fully decoded -- see the
Portal class. The x/y BSP nodes and sink nodes are an acceleration structure for
point-to-trapezoid lookup, which `containing()` already does by banding; they
are still read as sized blocks and skipped, and nothing needs them.

CROSSING BETWEEN PLANES, and how it was settled without guessing. Intra-plane
links alone leave Kamadan in 61 components with the largest at 17%. Two readings
of the portal record were tried and refuted, and an (x, y) overlap heuristic that
matched 90% of Kamadan's portal trapezoids was deliberately NOT shipped, because
it is our rule rather than the file's -- and with no height (below) it would join
a bridge to the ground beneath it.

What settled it was reading the client. `Gw.exe` carries ArenaNet's own asserts:
`PathDir.cpp` checks `m_trapezoid->portalLeft < pathMap.portalCount`, so a
trapezoid's two portal fields index its own plane's portal array -- which holds
on 3,051 and 3,095 set values with no exception -- and `PathDataImport.cpp`
checks `!pairRef->portal->pair`, which says the pairing is RESOLVED at import
rather than stored. The id it resolves through is the portal field this file
called `unknown` for a day: every value is shared by exactly two portals, 1,517
pairs covering all 3,034, always across the boundary they name.

Linking through it takes Kamadan from 61 components to **4, the largest holding
93%**, and Pre-Searing from 91 to 15 with the largest at 78%. That jump is
itself evidence: a wrong pairing does not assemble a map.

route() still returns None rather than a doubtful path, and now does so by
construction -- every segment of a path is re-checked before it is returned.

THERE IS NO HEIGHT. Planes are not elevations in any units we can read; nothing
in the file says what z a plane sits at, and GWToolbox fabricates one on load.
walkable() therefore asks "walkable on ANY plane", which is right for flat
ground and wrong under a bridge. Said plainly because it will matter later --
and it is exactly why an (x, y) overlap rule for cross-plane links is dangerous:
a bridge and the ground beneath it overlap perfectly.

THE TAIL, AND WHY IT MATTERS. This paragraph was written when route() had zero
callers; its first production consumer landed 2026-08-26 -- the player-click
router (`authsrv.py --router`, ROUTER-B2, studies/movement/ROUTER.md), which
answers clicks on the recv thread. `enemy_move_tick` still walks a straight
line and stops at the first wall -- the monster AI remains the staged second
consumer -- and the world runs on ONE thread with a 50 ms tick. So the worst
case is not a nicety: a route that takes six tick periods is six ticks in
which nothing in the world moves, and an intermittent whole-world freeze is
the hardest kind of failure to attribute to anything.

MEASURED on Pre-Searing (file id 0x1B97D, 6,120 trapezoids), 1,500 routes whose
endpoints are 150 to 1,200 units apart -- the band `enemy_move_tick` actually
chases in, between ENEMY_MELEE_RANGE and AGGRO_RANGE:

    p50 0.377 ms   p90 2.04   p99 32.1   p99.9 313.1   max 336.0 ms

336 ms is 6.7 tick periods, and 11 of the 1,500 (0.73%) blew a whole tick.
Eight hostiles re-pathing once a second reaches that about every seventeen
seconds.

**The A* was not the cause, and neither was any one thing.** A per-phase split
put the search at 3.5% and the string pull at 94.2%, and a previous attempt that
reported a "50.7x heapq speedup" is recorded as REFUTED -- the variant it timed
had skipped the smoothing pass entirely. Three things were measured one at a
time (all 1,500 pairs, same seed) and each is kept because it earned its place:

  * walkable() over a 2-D bucket of flattened trapezoids instead of a y-band of
    objects. 5.82 us -> 1.23 us a call on Pre-Searing, 3.34 -> 1.04 on Kamadan.
    Alone: max 336 -> 69.6 ms, still 2 routes over a tick.
  * the smoother's line test asks its samples COARSEST FIRST rather than
    front to back. The sample SET is unchanged, so the verdict is unchanged; a
    blocked line is simply refuted after a handful of samples instead of after
    walking all the way up to the wall, and most of the smoother's line tests
    are blocked. Alone: max 336 -> 64.3 ms, 1 route over a tick.
  * a connected-component pre-check, so a goal in another component costs O(1)
    instead of exhausting the component. This one measured NOTHING on its own
    (max 323.7 ms, still 11 over a tick) and looked worthless -- the failed
    searches were hiding underneath the smoother. With the other two in place it
    is the whole remaining tail: the five slowest routes left were all failed
    searches popping ~5,100 trapezoids each.

Together: **p50 0.185 ms, p90 0.733, p99 3.97, p99.9 9.96, max 16.6 ms, and 0
of 1,500 over a tick** -- and 0 of 1,500 returned paths differ from what the
old code returned, which is the claim that makes the rest of it safe. All three
are answer-preserving by construction: the bucket is the same point test with
the arithmetic pulled flat, the reordering does not change a set, and union-find
over the UNDIRECTED form of adjacent()'s relation OVER-approximates reachability,
so "different components" implies unreachable and never the reverse.

What is NOT answer-preserving is PULL_SAMPLE_BUDGET, and it is deliberately set
where nothing measured reaches it: see the constant.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archive import Archive, ffna_chunks, file_id_table  # noqa: E402

PATHING_CHUNK = 0x20000008
# Both MEASURED against Kamadan's bytes, not taken on faith: OpenTyria states
# them and the file agrees.
SIGNATURE = 0xEEFE704C
VERSION = 12

TAG_PLANES = 8
TERMINATOR = 255

TRAPEZOID = struct.Struct("<4I2H6f")
TRAPEZOID_SIZE = TRAPEZOID.size          # 44
PORTAL_SIZE = 9

PLANE_HEADER_FIELDS = ("polyData", "edgeVectors", "trapezoids", "xNodes",
                       "yNodes", "sinkNodes", "portals", "portalTraps")

# (tag, count field, bytes per element). None means the block is not
# count-driven -- tag 0 is the header itself and tag 3 is a single byte.
PLANE_LAYOUT = ((0, None, None), (11, "polyData", 8), (1, "edgeVectors", 8),
                (2, "trapezoids", TRAPEZOID_SIZE), (3, None, None),
                (4, "xNodes", 16), (5, "yNodes", 12), (6, "sinkNodes", 4),
                (10, "portalTraps", 4), (9, "portals", 9))

# Trapezoids are short in y -- Kamadan's are tens of units tall -- so bucketing
# on y turns the point test into a handful of comparisons instead of 1,270.
BAND = 256.0

# The same idea in two dimensions, for walkable() only. A y band alone still
# hands the point test every trapezoid at that latitude, which on Pre-Searing is
# tens of them across 40,000 units of longitude. MEASURED at 128/256/512 on both
# maps: 256 wins on Pre-Searing (1.41 / 1.23 / 1.44 us) and is within noise of
# 128 on Kamadan (0.90 / 1.04 / 1.51), so one number serves both. Build cost is
# 26 ms for Pre-Searing and 4 ms for Kamadan, paid lazily on the first
# walkable() -- the map corpus sweep in test_pathmap.py constructs a PathingMap
# for every map in the archive just to check the layout walks, and charging all
# 349 of them for a grid nothing asks about would be minutes of nothing.
CELL = 256.0

# How much x slack a trapezoid gets when it is filed into that grid, in map
# units. The bucket range comes from the record's own corner x values, but the x
# the point test compares against is a LERP between them, and a lerp is not
# guaranteed by IEEE to land inside the hull of its endpoints once rounding is
# involved. At map magnitudes (~1e4) the error is around 1e-12, so a whole unit
# of slack is free against a 256-unit cell and makes the question moot. Without
# it walkable() could miss a trapezoid containing() would have found, on one
# point in an eternity -- which is precisely the defect nobody can reproduce
# afterwards.
#
# AND NOTHING CHECKS IT, which is said here rather than left to be discovered.
# Setting this to 0.0 was built as a sabotage and RUN, and test_pathmap.py went
# green: 120,000 random points, 349 maps and 1,500 routes never produced the
# rounding case. So this is belt-and-braces on an argument, not a measured
# property, and it is the one line in this file with no experiment behind it.
CELL_SLACK = 1.0

# The most walkable() samples ONE _string_pull may spend before it stops trying
# to shorten the path and simply copies the rest of the waypoints through.
#
# This is the only thing here that can change an answer, so it is set from the
# measurement rather than from taste: over 1,500 routes in the chase band the
# worst pull spent 7,351 samples on Pre-Searing and 1,368 on Kamadan, so 20,000
# is 2.7x above anything observed and NOTHING in the corpus reaches it (0 of
# 1,463 returned paths change length). It is a backstop, not a policy -- the
# smoother is still quadratic in waypoints in the worst case, Pre-Searing is one
# sample of map-shape space, and a ceiling nobody hits is the difference between
# "fast on the maps we measured" and "cannot blow the tick".
#
# When it does bite, it degrades the way a smoother should: the remaining
# waypoints are the A*'s own, each on an edge shared by two trapezoids, so the
# path gets LONGER and never invalid. It cannot make route() return None that
# would otherwise have returned a path unless the un-smoothed tail contains a
# segment route()'s own final gate rejects -- which is why the None rate is
# asserted equal before and after in test_pathmap.py rather than assumed.
PULL_SAMPLE_BUDGET = 20000

# `_pull_corners`: how many Gauss-Seidel sweeps slide the crossings toward the
# taut line, how far each stays off its interval's ends, and when to stop early.
#
# ROUNDS is a budget, not a convergence proof. One sweep already fixes the R5
# specimen (a crossing whose neighbours are both fixed points needs exactly
# one), and the sweep is O(waypoints) against _string_pull's quadratic
# line-sampling, so this is noise in route()'s cost. More sweeps buy tautness on
# long chains where each move shifts its neighbour's answer; EPS stops as soon
# as a whole sweep moves nothing worth another pass.
#
# INSET keeps the answer off the exact interval end, which is the corner shared
# with the NEXT trapezoid along and the place a float containment test can fall
# either way -- sec.1w spent a lane's evidence on 1e-4 u excursions of exactly
# that kind, seen from the other side. It is capped at a quarter-span so a
# narrow doorway never insets itself shut.
CORNER_PULL_ROUNDS = 4
CORNER_PULL_INSET = 8.0
CORNER_PULL_EPS = 0.5

# The step the PULLED candidate's segments are re-sampled at before route()
# accepts them. It is `authsrv.A2_LEAD_CLIP_STEP` and `routerbench.py`'s scoring
# step, deliberately: the server re-clips every leg at 2.0 u before it sends,
# so a path this file calls legal at 16 u and the server then refuses is a
# disagreement between two of our own components -- which is the one kind of
# agreement this repo does not count as evidence. Duplicated rather than
# imported for the same reason CHASE_LO/HI are in test_pathmap.py: mapdata must
# not depend on the server, and the number being written here is what makes a
# future divergence findable.
CORNER_PULL_GATE_STEP = 2.0

# THE SEAM-AWARE ROUTE (MOVECODE-1z-bb, 2026-09-04). route()'s string pull and
# its final gate used to ask clip(), which asks "inside any trapezoid, on ANY
# plane" -- so the pull could drop the waypoints the A* only reached through a
# portal and grant a straight leg across a plane change the file carries no
# portal for. RUN-1zBA measured what that costs on a router grant: the drawn
# body parked at the bridge deck's edge (x = 10860.0, velocity 0) for 7.1 s and
# 7.5 s while the server's copy walked 2 km, then a 2,021 u teleport at the
# leg's ETA and the client's AgTrack fence shut (studies/movecode/FINDINGS.md
# sec.1z-ba). Both specimens came through the router's clip FALLBACK; the pull's
# sightline is the same primitive.
#
# The test that replaces it is a SEAM test, not the lead's plane test.
# `clip(plane=)` (MOVECODE-1z-ap) stops at ANY plane change, portals included --
# right for a 520 u keyboard lead the client is authoritative over, wrong for a
# router that must cut through every bridge. Here a plane change is legal iff a
# portal joins the two sides AT THAT POINT: `portal_at` gathers every trapezoid
# within SEAM_TOL of the seam on each side and asks `_cross` about the pairs.
# Three facts about the file make that the right shape (sec.1z-ba.1): portal
# links are a CLUSTER relation (every trapezoid on portal P links every one on
# its partner -- linked trapezoids are usually not adjacent), a seam is
# DIRECTIONAL (the plane the body is ON must end; the ground continuing under a
# deck is no seam for the ground), and the portal trapezoids are ZERO-HEIGHT
# LINES lying on the seam edges, which is why the tolerance exists at all -- a
# point test half a unit either side of a seam never lands on one.
#
# SEAM_AWARE_ROUTE is the revert (authsrv's --router-blind-clip clears it) and
# the known-bad arm test_pathmap.py section 14 drives: with it False the
# synthetic bridge routes as the straight line through its side, exactly the
# defect. SEAM_STEP is the server's own gate step; a sliver narrower than it
# would be stepped over, and no plane on either measured map is that narrow.
SEAM_AWARE_ROUTE = True
SEAM_TOL = 1.0
SEAM_STEP = 2.0


NO_NEIGHBOUR = 0xFFFFFFFF
NO_PORTAL = 0xFFFF


class Portal:
    """A crossing between two planes.

    Nine bytes, and three of the five fields are MEASURED rather than taken
    from a source, because each one has a check the file can fail:

      traps     u16   how many of this plane's trapezoids touch the crossing.
                      Summed over a plane's portals this equals the plane's
                      own portalTraps count -- 1,168 of 1,168 planes, zero
                      exceptions, and the two numbers live in different records.
      offset    u16   where this portal's run starts in the plane's portalTraps
                      array. The [offset, offset+traps) slices PARTITION that
                      array exactly -- every entry covered once, no overlap and
                      no gap, on 396 of 396 planes that have portals. All 6,146
                      indices so covered are valid trapezoids of their own plane.
      neighbour u16   the plane on the other side. In range on 3,034 of 3,034
                      portals, and the plane-to-plane relation is reciprocal
                      764 of 764 times.
      pair_id   u16   the crossing this portal is one side of. Two portals
                      share a value and no more than two ever do: across 3,034
                      portals the values fall into 1,517 groups of EXACTLY two,
                      with no singleton and no triple, and in 3,034 of 3,034
                      the partner sits in the plane this portal names and names
                      this plane back.

                      It is an IDENTIFIER, not an index, and reading it as one
                      is what hid it. Its values are always below the map's
                      total portal count, which makes "a global portal index"
                      the obvious guess -- and that guess is refuted, pairing
                      reciprocally 0 times out of 3,034. Recorded because the
                      wrong reading looks right.
      flag      u8    zero on all 3,034 portals seen. No information.

    The client computes the pairing rather than reading it: `PathDataImport.cpp`
    asserts `!pairRef->portal->pair` before filling it in, so `pair` is a
    resolved pointer and the id above is what it resolves through.
    """

    __slots__ = ("plane", "index", "traps", "offset", "neighbour",
                 "pair_id", "flag")

    def __init__(self, plane, index, traps, offset, neighbour, pair_id, flag):
        self.plane = plane
        self.index = index
        self.traps = traps
        self.offset = offset
        self.neighbour = neighbour
        self.pair_id = pair_id
        self.flag = flag

    def __repr__(self):
        return (f"<Portal p{self.plane}#{self.index} -> plane "
                f"{self.neighbour}, {self.traps} trapezoid(s)>")


def _nearest_on_segment(px, py, ax, ay, bx, by):
    """(x, y, dist) -- the nearest point of segment AB to P. Perpendicular
    projection clamped to the segment, which is what an axis clamp is not."""
    dx, dy = bx - ax, by - ay
    d2 = dx * dx + dy * dy
    if d2 <= 0.0:
        return ax, ay, ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = ((px - ax) * dx + (py - ay) * dy) / d2
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    qx, qy = ax + t * dx, ay + t * dy
    return qx, qy, ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5


def _nearest_on_trapezoid(t, x, y):
    """(x, y, dist) -- the exact nearest point of a trapezoid to (x, y).

    Zero when the point is inside. Otherwise the nearest point of a convex
    region's exterior lies on its boundary, so it is the best of the four
    edges -- corners included, because a segment projection clamps to them.
    """
    if t.contains(x, y):
        return x, y, 0.0
    cor = ((t.x_bottom_left, t.y_bottom), (t.x_bottom_right, t.y_bottom),
           (t.x_top_right, t.y_top), (t.x_top_left, t.y_top))
    best = None
    for i in range(4):
        ax, ay = cor[i]
        bx, by = cor[(i + 1) & 3]
        qx, qy, d = _nearest_on_segment(x, y, ax, ay, bx, by)
        if best is None or d < best[2]:
            best = (qx, qy, d)
    return best


class Trapezoid:
    """One walkable quad: a y span whose left and right edges are lines.

    Field names are the source's. The geometry is ours to check, and does.

    `neighbours` is the plane-local index of the trapezoid across each edge, in
    the source's order (top-left, top-right, bottom-left, bottom-right), with
    NO_NEIGHBOUR for a wall. This is the routing graph; see the module header
    for what makes it evidence rather than a field name.
    """

    __slots__ = ("plane", "index", "y_top", "y_bottom",
                 "x_top_left", "x_top_right", "x_bottom_left", "x_bottom_right",
                 "neighbours", "portal_left", "portal_right")

    def __init__(self, plane, index, y_top, y_bottom,
                 x_top_left, x_top_right, x_bottom_left, x_bottom_right,
                 neighbours=(), portal_left=0xFFFF, portal_right=0xFFFF):
        self.plane = plane
        self.index = index
        self.y_top = y_top
        self.y_bottom = y_bottom
        self.x_top_left = x_top_left
        self.x_top_right = x_top_right
        self.x_bottom_left = x_bottom_left
        self.x_bottom_right = x_bottom_right
        self.neighbours = neighbours
        self.portal_left = portal_left
        self.portal_right = portal_right

    @property
    def centre(self):
        y = (self.y_top + self.y_bottom) * 0.5
        x = (self.x_top_left + self.x_top_right
             + self.x_bottom_left + self.x_bottom_right) * 0.25
        return x, y

    def contains(self, x, y):
        if not (self.y_bottom <= y <= self.y_top):
            return False
        span = self.y_top - self.y_bottom
        f = 0.0 if span <= 0.0 else (y - self.y_bottom) / span
        left = self.x_bottom_left + f * (self.x_top_left - self.x_bottom_left)
        right = self.x_bottom_right + f * (self.x_top_right - self.x_bottom_right)
        return left <= x <= right

    def __repr__(self):
        return (f"<Trapezoid p{self.plane}#{self.index} "
                f"y {self.y_bottom:.0f}..{self.y_top:.0f}>")


class PathingMap:
    """Every trapezoid in one map, with a point test over them."""

    def __init__(self, trapezoids, planes, portals=None, portal_traps=None):
        self.trapezoids = trapezoids
        self.planes = planes
        self.portals = portals or []
        self.portal_traps = portal_traps or []
        self._bands = {}
        for t in trapezoids:
            lo = int(t.y_bottom // BAND)
            hi = int(t.y_top // BAND)
            for b in range(lo, hi + 1):
                self._bands.setdefault(b, []).append(t)
        # Plane-local indices are what the file stores; routing wants one flat
        # space. `_base[p]` is where plane p's trapezoids start in self.trapezoids.
        self._base = {}
        for i, t in enumerate(trapezoids):
            self._base.setdefault(t.plane, i)
        self._cross = self._build_cross_links()
        # Both built on first use, never here: from_chunk() runs on every map
        # in the archive during the corpus sweep, and neither of these is worth
        # a millisecond to a caller that only wants to know the layout walked.
        self._grid = None            # walkable()'s bucket; _build_grid
        self._component = None       # route()'s reachability; _build_components

    def _build_cross_links(self):
        """Trapezoid-to-trapezoid links through paired portals.

        Two things make this a decode rather than a guess, and both are the
        client's own words. `PathDir.cpp` asserts
        `m_trapezoid->portalLeft < pathMap.portalCount`, so a trapezoid's two
        portal fields index its OWN plane's portal array -- which holds on
        3,051 and 3,095 of the set values, with no exception. And portals pair
        by their `pair_id`, exactly two to a value, always across the plane
        boundary they name.

        So a trapezoid sitting on a portal is linked to the trapezoids sitting
        on that portal's partner. No geometry is consulted and nothing is
        inferred from (x, y) overlap, which matters because with no height in
        the file an overlap rule would join a bridge to the ground beneath it.
        """
        by_pair = {}
        for row in self.portals:
            for p in row:
                by_pair.setdefault(p.pair_id, []).append(p)
        # Which trapezoids sit on each (plane, portal index)?
        on = {}
        for i, t in enumerate(self.trapezoids):
            for k in (t.portal_left, t.portal_right):
                if k != NO_PORTAL:
                    on.setdefault((t.plane, k), []).append(i)
        links = {}
        for group in by_pair.values():
            if len(group) != 2:
                continue          # not a clean pair; say nothing about it
            a, b = group
            ta = on.get((a.plane, a.index), ())
            tb = on.get((b.plane, b.index), ())
            for i in ta:
                links.setdefault(i, []).extend(tb)
            for j in tb:
                links.setdefault(j, []).extend(ta)
        return links

    def _build_grid(self):
        """walkable()'s 2-D bucket: (cell y, cell x) -> flattened trapezoids.

        This is `Trapezoid.contains` with the arithmetic pulled out flat and the
        candidate set narrowed in x as well as y. It exists because walkable()
        is the inner loop of everything: a single route() in the chase band
        spends up to 73,908 calls in here, and at the 5.82 us an attribute-and-
        method-call version costs that is 284 ms on the thread that owns the
        world. Flat tuples take it to 1.23 us.

        THE ARITHMETIC IS BIT-FOR-BIT `contains`. `dxl` is `x_top_left -
        x_bottom_left` computed once instead of once per call, and IEEE
        subtraction is deterministic, so `xbl + f * dxl` is the same float
        `contains` computes. That matters more than the speed: this is a SECOND
        implementation of the point test, and `containing()` deliberately still
        runs the first one, so test_pathmap.py can put the two against each
        other over a large random sample and get a real answer rather than a
        tautology.

        The x span is padded by CELL_SLACK -- see the constant for the one way
        this could otherwise disagree with `contains`.
        """
        grid = {}
        for t in self.trapezoids:
            yb, yt = t.y_bottom, t.y_top
            xmn = min(t.x_bottom_left, t.x_top_left) - CELL_SLACK
            xmx = max(t.x_bottom_right, t.x_top_right) + CELL_SLACK
            # The plane rides along as a tenth field so planes_at() can be
            # answered from this same bucket at walkable()'s cost; walkable()
            # ignores it.
            rec = (yb, yt, yt - yb,
                   t.x_bottom_left, t.x_bottom_right,
                   t.x_top_left - t.x_bottom_left,
                   t.x_top_right - t.x_bottom_right,
                   xmn, xmx, t.plane)
            # An inverted y span files into no cell at all, which agrees with
            # `contains` -- it can never satisfy y_bottom <= y <= y_top either.
            for cy in range(int(yb // CELL), int(yt // CELL) + 1):
                for cx in range(int(xmn // CELL), int(xmx // CELL) + 1):
                    grid.setdefault((cy, cx), []).append(rec)
        return {k: tuple(v) for k, v in grid.items()}

    # -- queries ---------------------------------------------------------

    def containing(self, x, y):
        """Every trapezoid holding this point. Usually zero or one.

        Still the y-band walk over Trapezoid objects. walkable() has its own
        faster path and this one is the control on it; keeping both is the
        point, and this one is called twice per route() rather than tens of
        thousands of times.
        """
        return [t for t in self._bands.get(int(y // BAND), ())
                if t.contains(x, y)]

    def walkable(self, x, y):
        """Is this point inside any trapezoid, on any plane? See _build_grid."""
        grid = self._grid
        if grid is None:
            grid = self._grid = self._build_grid()
        for (yb, yt, span, xbl, xbr, dxl, dxr, xmn, xmx, _pl) in \
                grid.get((int(y // CELL), int(x // CELL)), ()):
            if xmn <= x <= xmx and yb <= y <= yt:
                f = 0.0 if span <= 0.0 else (y - yb) / span
                if xbl + f * dxl <= x <= xbr + f * dxr:
                    return True
        return False

    def planes_at(self, x, y):
        """The set of planes with a trapezoid under this point, at walkable()'s
        cost. Empty off the mesh. The same arithmetic as walkable(), so the two
        cannot disagree about whether a point is on the mesh at all."""
        grid = self._grid
        if grid is None:
            grid = self._grid = self._build_grid()
        out = set()
        for (yb, yt, span, xbl, xbr, dxl, dxr, xmn, xmx, pl) in \
                grid.get((int(y // CELL), int(x // CELL)), ()):
            if xmn <= x <= xmx and yb <= y <= yt:
                f = 0.0 if span <= 0.0 else (y - yb) / span
                if xbl + f * dxl <= x <= xbr + f * dxr:
                    out.add(pl)
        return out

    def on_mesh(self, x, y, tol=SEAM_TOL):
        """Is (x, y) on the mesh AS THE CLIENT RESOLVES IT: inside a trapezoid,
        or within `tol` of one. `walkable()` is exact containment, and the
        client's own copies stand where exact containment says nothing is.

        MEASURED (MOVECODE-1z-bf, 2026-09-04). Every gate2-offmesh re-pin in the
        harness corpus -- 17 of 17 fired, 19 of 19 predicted, over 1,123 runs --
        was raised with the modelled sync copy standing on a point walkable()
        rejects by <= 0.5 u, at the wedge tip of map 146 where the client's
        own navmesh trace lays its waypoints ALONG trapezoid edges (the first
        quarterstep of a keyboard walk lands 0.01-0.03 u outside the plane by
        our decode, sec.1z-bd.2). The client reported its body standing on
        those points, and on the two hooked runs its own snap test ran on the
        very grant we vetoed and did not reseed (sec.1z-bf). So a sub-unit
        sliver outside our edge is not off the client's mesh; it is our edge
        rounding. `tol` defaults to SEAM_TOL, the same 1 u that lets
        portal_at() see zero-height portal lines -- one constant for "the
        mesh as the client sees it at its edges", not a new guess. A caller
        that needs "which plane" still uses planes_at()/plane_at(), which this
        deliberately does not widen: the slivers here are at portal ENDS,
        where two planes meet, and naming one would be the guess this method
        exists to avoid making.
        """
        if self.walkable(x, y):
            return True
        return bool(self._near(x, y, tol))

    def _near(self, x, y, tol=SEAM_TOL):
        """Every trapezoid within `tol` of (x, y) -- zero-height portal lines
        included, which containing() can only hit by landing on them exactly."""
        out = []
        for b in range(int((y - tol) // BAND), int((y + tol) // BAND) + 1):
            for t in self._bands.get(b, ()):
                if not (t.y_bottom - tol <= y <= t.y_top + tol):
                    continue
                if not (min(t.x_bottom_left, t.x_top_left) - tol <= x
                        <= max(t.x_bottom_right, t.x_top_right) + tol):
                    continue
                if _nearest_on_trapezoid(t, x, y)[2] <= tol:
                    out.append(t)
        return out

    def portal_at(self, x, y, planes_from, planes_to, tol=SEAM_TOL):
        """Is there a portal at (x, y) from any of `planes_from` to any of
        `planes_to`? True iff some trapezoid within `tol` on the from side is
        `_cross`-linked to some trapezoid within `tol` on the to side."""
        near = self._near(x, y, tol)
        A = [self._flat_index(t) for t in near if t.plane in planes_from]
        B = [self._flat_index(t) for t in near if t.plane in planes_to]
        cross = self._cross
        for a in A:
            links = cross.get(a, ())
            for b in B:
                if b in links or a in cross.get(b, ()):
                    return True
        return False

    def seam_clip(self, x0, y0, x1, y1, plane, step=SEAM_STEP):
        """How far a body ON `plane` gets along (x0,y0)->(x1,y1) before it
        leaves the mesh or its plane ends without a portal.

        clip() with a seam term (MOVECODE-1z-bb). Samples like clip(); carries
        the set of planes the body is on -- {plane} if the start offers it,
        else every plane the start offers -- and a sample that keeps any of
        them is a step, not a change (a sample landing exactly on a shared
        edge lies in both trapezoids and must not read as a crossing; a deck
        over continuing ground is a seam for the deck and not for the ground).
        When every carried plane has ended, the seam is bisected from both
        sides and `portal_at` asked; a portal lets the walk continue on the
        new planes, anything else returns the last sample before the change.
        A sample in no trapezoid returns the last one, as clip() does.

        Returns the point, like clip(). `_seam_walk` is the same walk
        returning its sample count too, for the pull's budget.
        """
        return self._seam_walk(x0, y0, x1, y1, plane, step)[0]

    def _seam_walk(self, x0, y0, x1, y1, plane, step=SEAM_STEP, strict=True):
        """seam_clip's body -> (point, samples spent).

        `strict` decides what an off-mesh sample means. True (the gate,
        seam_clip itself): stop there, as clip() does. False (the pull's
        acceptance test): skip it -- walkability is `_sightline`'s job at
        its own 16 u resolution, and a 2 u seam walk that also refused
        sub-sample cracks changed 35 of 300 chase-band paths that crossed no
        seam at all (MEASURED before this flag existed). The seam walk judges
        plane changes and nothing else.
        """
        dx, dy = x1 - x0, y1 - y0
        dist = (dx * dx + dy * dy) ** 0.5
        if dist <= 0.0:
            return (x0, y0), 0
        n = max(1, int(dist / step))
        planes_at = self.planes_at
        carried = None
        last = (x0, y0)
        prev_f = 0.0
        spent = 0
        for i in range(0, n + 1):
            f = i / n
            px, py = x0 + dx * f, y0 + dy * f
            cp = planes_at(px, py)
            spent += 1
            if not cp:
                if i == 0 or not strict:
                    continue                  # off-mesh: not this walk's call
                return last, spent
            if carried is None:
                carried = {plane} if (plane is not None and plane in cp) else cp
            elif carried & cp:
                carried = carried & cp
            else:
                # the carried planes ended between prev_f and f: find where
                lo, hi = prev_f, f
                for _ in range(12):
                    mid = (lo + hi) * 0.5
                    if planes_at(x0 + dx * mid, y0 + dy * mid) & carried:
                        lo = mid
                    else:
                        hi = mid
                f_old = lo
                lo, hi = prev_f, f
                for _ in range(12):
                    mid = (lo + hi) * 0.5
                    if planes_at(x0 + dx * mid, y0 + dy * mid) & cp:
                        hi = mid
                    else:
                        lo = mid
                f_new = hi
                sf = (f_old + f_new) * 0.5
                spent += 24
                if not self.portal_at(x0 + dx * sf, y0 + dy * sf, carried, cp):
                    return last, spent
                carried = cp
            last = (px, py)
            prev_f = f
        return (x1, y1), spent

    def _gate_clip(self, a, b, plane, step):
        """route()'s per-segment gate: the seam-aware walk when the corridor
        plane is known and SEAM_AWARE_ROUTE is on, else clip() as before."""
        if SEAM_AWARE_ROUTE and plane is not None:
            return self.seam_clip(a[0], a[1], b[0], b[1], plane, step=step)
        return self.clip(a[0], a[1], b[0], b[1], step=step)

    def nearest_walkable(self, x, y, radius):
        """(px, py, dist) -- the nearest on-mesh point within radius, or None.

        ROUTER-B5 (2026-08-26 run 3): a client can legitimately STAND a few
        units outside this decode -- measured penetrations 0.25u (the P-17
        wall press) and 8.0u (run 3's parked stop beside a plane-44
        structure, which turned into 218 seconds of origin-off-mesh click
        refusals and ended in the client's own 3.2km reconcile snap when
        the keyboard finally spoke). A caller that needs a routable origin
        asks for the nearest covered point instead of refusing outright.

        THE DISTANCE IS EXACT AS OF 2026-08-29, AND IT WAS NOT BEFORE.
        This used to find the candidate by clamping y into the trapezoid's
        span and then x into its edges AT THAT Y -- an axis clamp, which is
        the true nearest point only when the edge it lands on is axis-aligned.
        Against a slanted edge it walks along y and then along x instead of
        projecting perpendicularly, and the docstring's claim that "within the
        small radii this is for the error is bounded" quietly stopped holding
        the moment an offline scorer asked at radius 600: measured over r7's
        67 off-mesh endpoints against dense boundary sampling, it over-reported
        by up to 2.967x (77.43 u where the truth is 26.10 u) and by up to
        64.91 u absolute. `noclipscore.py` quotes this value as "how far
        off-mesh", so every depth in an r6/r6b-era scoring pass that cited it
        carries that error.

        Now it is the exact euclidean nearest point on the trapezoid, which
        for a convex quad is the nearest point on its four EDGES (or the point
        itself when inside). Cost is four segment projections per candidate
        instead of one clamp, paid back by a bounding-box lower bound that
        skips a candidate before any of them -- the large-radius case this was
        wrong for is the one the early-out helps most.

        Every returned point is still VERIFIED walkable() (a projection
        landing on a boundary float is nudged toward the trapezoid's centre
        first; a candidate that still fails verification is skipped, never
        returned) -- and THE DISTANCE IS NOW RECOMPUTED AFTER THAT NUDGE, so
        the point and the distance describe each other. It used to return the
        pre-nudge distance beside a post-nudge point."""
        best = None
        b0 = int((y - radius) // BAND)
        b1 = int((y + radius) // BAND)
        for band in range(b0, b1 + 1):
            for t in self._bands.get(band, ()):
                # A cheap lower bound on the distance to this trapezoid: the
                # distance to its bounding box. Skipping here costs two
                # comparisons and saves four projections.
                xlo = t.x_bottom_left if t.x_bottom_left < t.x_top_left \
                    else t.x_top_left
                xhi = t.x_bottom_right if t.x_bottom_right > t.x_top_right \
                    else t.x_top_right
                ylo, yhi = t.y_bottom, t.y_top
                if ylo > yhi:
                    ylo, yhi = yhi, ylo
                dx = xlo - x if x < xlo else (x - xhi if x > xhi else 0.0)
                dy = ylo - y if y < ylo else (y - yhi if y > yhi else 0.0)
                lb = (dx * dx + dy * dy) ** 0.5
                if lb > radius or (best is not None and lb >= best[0]):
                    continue
                cx, cy, d = _nearest_on_trapezoid(t, x, y)
                if d > radius or (best is not None and d >= best[0]):
                    continue
                if not self.walkable(cx, cy):
                    # THE NUDGE ESCALATES FROM SMALL, and that matters to the
                    # distance now that the distance is exact. A flat 1e-3 of
                    # the way to the centre is ~0.5 u on a 500 u trapezoid --
                    # which was invisible beside the old 65 u error and is the
                    # dominant term once that is gone. Take the smallest step
                    # that clears the float boundary rather than a fixed one.
                    ctr = t.centre
                    for f in (1e-6, 1e-5, 1e-4, 1e-3, 1e-2):
                        nx = cx + (ctr[0] - cx) * f
                        ny = cy + (ctr[1] - cy) * f
                        if self.walkable(nx, ny):
                            cx, cy = nx, ny
                            break
                    else:
                        continue
                    # RECOMPUTE: the nudge moved the point, so the old `d`
                    # described a point we are not returning.
                    d = ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5
                    if d > radius or (best is not None and d >= best[0]):
                        continue
                best = (d, cx, cy)
        if best is None:
            return None
        return best[1], best[2], best[0]

    def plane_at(self, x, y, prefer=None):
        """Which plane a point is on, or None if the geometry cannot say.

        THE PLANE INDICES IN THIS FILE ARE THE ONES THE CLIENT USES. MEASURED
        over 198 position-and-plane reports from a real client across four
        sessions: 189 landed inside a trapezoid whose plane index was exactly
        the plane the client named -- 0 to 0 (148 times), 12 to 12, 5 to 5, 4 to
        4, 3 to 3. That is the first thing tying the archive's geometry to the
        wire protocol, and it means a destination's plane can be computed
        instead of guessed.

        The other 9 were all "client says 12, we find 0", which is not an error
        so much as the known limitation showing through: there is NO HEIGHT in
        the file, so a bridge and the ground beneath it are two planes occupying
        the same (x, y). Where the answer is ambiguous this returns `prefer` if
        it is one of the candidates -- a player is usually still on the plane
        they were on -- and None when it genuinely cannot tell. None means "say
        nothing", never a guess.
        """
        planes = {t.plane for t in self._bands.get(int(y // BAND), ())
                  if t.contains(x, y)}
        if not planes:
            return None
        if prefer in planes:
            return prefer
        if len(planes) == 1:
            return next(iter(planes))
        return None

    def clip(self, x0, y0, x1, y1, step=16.0, plane=None):
        """How far along (x0,y0)->(x1,y1) a character can actually get.

        Returns the last sampled point that is walkable, or the start if the
        very first step is not. Sampling, not solving: a gap narrower than
        `step` can be stepped over. 16 units is about a twentieth of a second at
        run speed, and the client does its own collision besides.

        `plane` -- STAY ON ONE SURFACE (MOVECODE-1z-ap). Default None is the
        historical behaviour to the bit: `walkable()` asks "inside any
        trapezoid, ON ANY PLANE", so a ray from a bridge to the ground beneath
        it clips CLEAR even though the two are different physical places with
        no straight walk between them. RUN-1zAO caught that costing a 520 u
        warp: the lead `(10373,8286) -> (9853,8286)` runs plane 29 -> plane 0,
        this method scored it clear at full length, the client would not walk
        it, and the drawn body was still parked when the grant's arrival
        teleported it onto the far end (FINDINGS sec.1z-ao.5).

        Given a plane, a sample must ALSO be on it -- `plane_at(prefer=plane)`,
        so the ambiguous stacked case resolves to `plane` when the mesh offers
        it there and to None ("say nothing") when it cannot tell, which clips.
        The plane term can only ever stop the walk EARLIER, never later, so it
        cannot lengthen a lead: the failure direction is a short grant, which
        the client is authoritative over anyway.

        Crossing to another surface is a PORTAL's job (`adjacent()` walks them
        and `route()` searches them); a straight-line clip is not the place to
        model one, and refusing to walk off the start plane is the conservative
        reading of a mesh with NO HEIGHT in it.
        """
        dx, dy = x1 - x0, y1 - y0
        dist = (dx * dx + dy * dy) ** 0.5
        if dist <= 0.0:
            return (x0, y0)
        n = max(1, int(dist / step))
        last = (x0, y0)
        for i in range(1, n + 1):
            f = i / n
            px, py = x0 + dx * f, y0 + dy * f
            if not self.walkable(px, py):
                return last
            if plane is not None and self.plane_at(px, py, prefer=plane) != plane:
                return last
            last = (px, py)
        return (x1, y1)

    # -- routing ---------------------------------------------------------

    def adjacent(self, t, flat=None):
        """The trapezoids reachable from `t` in one step, as flat indices.

        Neighbours within the plane, plus anything on the far side of a portal
        this trapezoid sits on.
        """
        base = self._base[t.plane]
        out = [base + n for n in t.neighbours if n != NO_NEIGHBOUR]
        if flat is None:
            flat = self._flat_index(t)
        out.extend(self._cross.get(flat, ()))
        return out

    def _flat_index(self, t):
        return self._base[t.plane] + t.index

    def _build_components(self):
        """Which trapezoids can reach which, as one root index per trapezoid.

        Union-find over EXACTLY the relation `adjacent()` walks -- this asks
        `adjacent()` itself rather than re-deriving the edges, so the two cannot
        drift apart. Pre-Searing comes out in 15 components with the largest
        holding 4,795 of 6,120; Kamadan's largest holds 93%.

        WHY THIS CANNOT CHANGE AN ANSWER, which is the only reason route() is
        allowed to skip a search on it. Union-find ignores direction, so it
        merges at least as much as directed reachability does: two trapezoids in
        DIFFERENT components have no undirected path and therefore no directed
        one, so the A* would have failed. Two in the same component may still be
        unreachable in principle, and the A* runs exactly as before. The
        over-approximating direction is the safe one and this is on that side.

        It measured NOTHING on its own -- max 323.7 ms, still 11 routes over a
        tick -- because the failed searches were sitting underneath the
        smoother. Once the smoother stopped costing 94% the five slowest routes
        left were all searches that popped ~5,100 trapezoids and then returned
        None, and this is what removes them. Recorded because a lever that
        measures zero in isolation is normally one to drop.
        """
        n = len(self.trapezoids)
        parent = list(range(n))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]          # path halving
                a = parent[a]
            return a

        for i, t in enumerate(self.trapezoids):
            for j in self.adjacent(t, i):
                # An out-of-range neighbour index is a broken file, and the A*
                # would raise on it. Skipping it here only ever splits a
                # component, which is the direction that costs a search rather
                # than the one that skips a real route -- and it keeps
                # from_chunk() over the whole corpus from gaining a new way to
                # die at load time.
                if not 0 <= j < n:
                    continue
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri
        return [find(i) for i in range(n)]

    def route(self, x0, y0, x1, y1, start_plane=None, goal_plane=None,
              with_planes=False):
        """A walkable path from start to goal, or None if there is not one.

        A* over the trapezoid adjacency graph, then a string-pulling pass that
        drops any waypoint the previous one can already see. The result is a
        list of points beginning at the start and ending at the goal; walking
        it in straight segments never leaves the navmesh.

        PLANE PREFERENCE (ROUTER-B4, 2026-08-26 run 2): `start_plane` /
        `goal_plane` restrict the containing-trapezoid candidates to the
        named plane WHEN a candidate on it exists -- prefer semantics, the
        same contract as plane_at(prefer=): a preference that nothing
        matches falls back to every candidate rather than refusing. This
        exists because endpoint selection used to take containing()[0]
        blind, and on stacked geometry (a prop top over terrain, a bridge
        over ground -- THERE IS NO HEIGHT in this file) that picked an
        arbitrary surface: the verification run's owner watched a click
        with a known plane route 12 waypoints around the island to the
        wrong stack level. The caller that knows the planes (the click
        carries the clicked surface's plane; the server tracks the
        player's) can now say so.

        `with_planes=True` returns (path, planes) with planes[i] the plane
        of the trapezoid path[i] enters (the start trapezoid's plane for
        path[0], the goal trapezoid's for the terminal) -- the corridor's
        own answer to "which plane word does this waypoint's grant carry",
        replacing per-point plane_at() guesses that are wrong exactly on
        the stacked geometry the route is threading.

        CROSSES PLANES via the portal-pair links (this paragraph used to say
        SAME PLANE ONLY, written before `pair_id` was decoded -- stale from
        the moment _build_cross_links shipped, caught by the 2026-08-26
        router review). adjacent() walks the cross links, _shared_edge
        delegates portal crossings to _overlap_point, and the residual
        hazard the old warning was about is real but HANDLED DOWNSTREAM:
        there is no height in this file, so a cross-plane step whose
        trapezoids do not (x,y)-overlap gets a fallback waypoint that can
        leave the mesh -- which the final per-segment clip() gate below
        catches, returning None rather than a path through a bridge.

        THIS RUNS ON THE WORLD THREAD, so its worst case is a budget and not a
        curiosity: MEASURED on Pre-Searing over 1,500 routes in the chase band,
        p50 0.163 ms and max 19.8 ms against a 50 ms tick, down from p50 0.395
        and max 346.6 -- see the module header for the three measurements and
        test_pathmap.py section 10 for the controls, of which the load-bearing
        one is that none of it changed a single returned path.
        """
        starts = self.containing(x0, y0)
        goals = self.containing(x1, y1)
        if not starts or not goals:
            return None
        if start_plane is not None:
            pref = [t for t in starts if t.plane == start_plane]
            starts = pref or starts
        if goal_plane is not None:
            pref = [t for t in goals if t.plane == goal_plane]
            goals = pref or goals
        goal_set = {self._flat_index(g) for g in goals}
        start = starts[0]
        si = self._flat_index(start)
        if si in goal_set:
            path = [(x0, y0), (x1, y1)]
            if with_planes:
                return path, [start.plane, start.plane]
            return path
        # A goal in another component is the A*'s WORST case, not a cheap miss:
        # it pops every trapezoid it can reach before giving up, which on
        # Pre-Searing is ~5,100 of them and was the entire remaining tail once
        # the smoother stopped dominating. Answering it here is the same None,
        # arrived at without the search -- see _build_components for why that is
        # a theorem rather than a bet.
        comp = self._component
        if comp is None:
            comp = self._component = self._build_components()
        home = comp[si]
        if all(comp[g] != home for g in goal_set):
            return None
        gi = next(iter(goal_set))
        gx, gy = x1, y1

        def h(i):
            cx, cy = self.trapezoids[i].centre
            return ((cx - gx) ** 2 + (cy - gy) ** 2) ** 0.5

        open_q = [(h(si), si)]
        came = {si: None}
        best = {si: 0.0}
        found = False
        while open_q:
            open_q.sort(reverse=True)
            _f, cur = open_q.pop()
            if cur in goal_set:
                gi = cur
                found = True
                break
            cx, cy = self.trapezoids[cur].centre
            for nxt in self.adjacent(self.trapezoids[cur], cur):
                nx, ny = self.trapezoids[nxt].centre
                step = ((nx - cx) ** 2 + (ny - cy) ** 2) ** 0.5
                g = best[cur] + step
                if g < best.get(nxt, float("inf")):
                    best[nxt] = g
                    came[nxt] = cur
                    open_q.append((g + h(nxt), nxt))
        if not found:
            return None

        chain = []
        cur = gi
        while cur is not None:
            chain.append(cur)
            cur = came[cur]
        chain.reverse()

        # Waypoints are the SHARED EDGES, not the centres. Two adjacent
        # trapezoids are both walkable, but the straight line between their
        # centres can leave the mesh when either is long and oblique -- which
        # it does in practice, and produced a path with an unwalkable segment
        # before this was fixed. A point on the edge they share is inside both
        # by construction.
        pts = [(x0, y0)]
        pls = [self.trapezoids[si].plane]
        spans = [None]
        for a, b in zip(chain, chain[1:]):
            pt, span = self._shared_edge(self.trapezoids[a],
                                         self.trapezoids[b], span=True)
            pts.append(pt)
            spans.append(span)
            pls.append(self.trapezoids[b].plane)
        pts.append((x1, y1))
        pls.append(self.trapezoids[gi].plane)
        spans.append(None)
        # Slide each crossing along its own edge BEFORE dropping any: the
        # midpoint rule aims a walker at the middle of an edge it should
        # cross beside itself, and _string_pull can only drop, never slide.
        # MOVECODE R5's backtrack -- see _pull_corners.
        #
        # THE PULL IS A CANDIDATE, NOT A REPLACEMENT, and that is the whole
        # safety argument. Each pulled point is still inside both trapezoids
        # it crosses between, but the SEGMENT between two pulled points can
        # cut a corner the midpoints rounded off -- measured, 4 of 300 corpus
        # routes lost their path to exactly that before this fallback existed.
        # So both candidates are gated and the shorter survivor wins: the pull
        # can only ever improve on the midpoint answer, never lose one.
        # THE GATE, and it is not belt-and-braces -- it is also what makes the
        # corner pull safe. A cross-plane step joins two trapezoids that the
        # file says share a crossing; where they do not also overlap in (x, y)
        # -- about a fifth of them in Pre-Searing -- the waypoint falls back to
        # the far trapezoid's centre and the straight line to it can leave the
        # mesh. And a PULLED point, while still inside both trapezoids it
        # crosses between, can leave a segment that cuts a corner the midpoints
        # rounded off: 4 of 300 corpus routes lost their path to exactly that
        # before this became a candidate contest. So both candidates are gated
        # and the shorter survivor wins -- the pull can only improve on the
        # midpoint answer, never lose one. Returning nothing is a worse answer
        # than a detour and a better one than a path through a wall.
        # BOTH CANDIDATES ARE SCORED AND THE SHORTER LEGAL ONE WINS. The cheap
        # version of this -- take the pulled path whenever it is legal, and only
        # fall back when it is not -- was BUILT AND REJECTED BY ITS OWN
        # MEASUREMENT: 7 of R5's 34 clicks came out LONGER that way, one of them
        # 3,697 -> 5,228 u, which is the "no player would accept this" class the
        # tour cap exists for. The tempting argument for it is wrong and worth
        # writing down: each pull move is the local minimiser, so the pulled
        # POLYLINE is never longer than the midpoints' -- but _string_pull runs
        # afterwards and DROPS waypoints, and a taut polyline can offer it fewer
        # droppable corners than a slack one. Shorter before the smoother does
        # not survive the smoother.
        #
        # THE PRICE, measured rather than waved at, because this runs on the
        # thread that owns the world and a 336 ms worst case here once cost the
        # campaign an unattributable world freeze. Two costs: a second
        # _string_pull (94% of route()), and the fine gate below. Over a
        # 300-route corpus sweep of cross-map centroid pairs -- a far harsher
        # distribution than clicks, whose routes run tens of thousands of units
        # -- p50 4.9 -> 10.5 ms, p95 12.9 -> 23.3 ms, max 20.8 -> 30.4 ms, and
        # **0 of 300 over a 50 ms tick in either arm**. Over R5's 34 real
        # clicks, 1.5 -> 3.0 ms mean. It is roughly double, it is inside the
        # budget, and the headroom is now the thing to watch: if a future map
        # puts p95 near the tick, the first lever is gating only the segments
        # the pull actually MOVED (the rest are the midpoint answer, already
        # shipped at 16 u for a year) rather than the whole pulled path.
        # THE PULLED CANDIDATE IS GATED AT THE FINER STEP, and this is not
        # symmetry-breaking for its own sake. clip() is a SAMPLER: a segment
        # that clears it at the default 16 u can still graze a sliver of
        # blocked ground between samples, and the pull is precisely what moves
        # crossings off the middle of an edge and out toward its ends, where
        # slivers live. `routerbench.py` re-clips at CORNER_PULL_GATE_STEP
        # because the server does before it sends -- and it CAUGHT this: the
        # first version of the pull was gated at 16 u, and the bench's
        # "every routed specimen's legs clip-clean" went red on a leg that
        # passed here and failed there. The fallback keeps the default step,
        # so the answer route() gave before the pull existed is untouched.
        pulled = self._pull_corners(pts, spans)
        best = None
        for cand in ((pulled, pts) if pulled is not pts else (pts,)):
            step = (CORNER_PULL_GATE_STEP if cand is pulled and pulled is not pts
                    else 16.0)
            # THE SEAM TERM (MOVECODE-1z-bb): the pull and the gate both carry
            # the corridor's plane per waypoint, so a shortcut is refused when
            # a body on the kept point's plane would reach a plane change no
            # portal covers. The A* corridor itself only ever steps across
            # links, so `pts` needs the term only against the shared-edge
            # fallback waypoint (a far centre when two linked trapezoids do
            # not overlap in 2D); the pulled candidate is where it bites.
            self._pull_idx = None
            cpath = self._string_pull(cand, planes=pls)
            # Each survivor's plane, by the INDEX the pull kept it at. The
            # pull records that (`_pull_idx`); a replacement pull that does
            # not (test_pathmap's pre-fix reconstruction) falls back to
            # value-matching, taking the LAST of a run of coincident points --
            # the pull tries farther indices first, and coincident points pass
            # or fail its tests identically, so that is the one it would keep.
            kept = self._pull_idx
            if (isinstance(kept, list) and len(kept) == len(cpath)
                    and all(cand[k] == p for k, p in zip(kept, cpath))):
                cpl = [pls[k] for k in kept]
            else:
                cpl, j = [], 0
                for k, p in enumerate(cpath):
                    while cand[j] != p:
                        j += 1
                    while (j + 1 < len(cand) and cand[j + 1] == p
                           and not (k + 1 < len(cpath) and cpath[k + 1] == p)):
                        j += 1
                    cpl.append(pls[j])
                    j += 1
            if any(self._gate_clip(a, b, pa, step) != b
                   for a, b, pa in zip(cpath, cpath[1:], cpl)):
                continue
            clen = sum(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
                       for a, b in zip(cpath, cpath[1:]))
            if best is None or clen < best[0]:
                best = (clen, cpath, cpl)
        if best is None:
            return None
        if with_planes:
            return best[1], best[2]
        return best[1]

    def _shared_edge(self, a, b, span=False):
        """A point on the edge `a` and `b` share, inside both.

        Across a portal the two trapezoids are the same physical place on two
        planes rather than neighbours on one, so there is no shared edge; the
        centre of where they overlap is inside both.

        `span=True` also returns `(lo, hi, y)` -- the whole interval the two
        share, which is what `_pull_corners` slides the crossing along. None
        for a portal crossing, whose point is not on a straight edge.
        """
        if a.plane != b.plane:
            pt = self._overlap_point(a, b)
            return (pt, None) if span else pt
        slot = next((k for k, n in enumerate(a.neighbours)
                     if n == b.index), None)
        if slot is None or slot < 2:
            y = a.y_top
            lo_a, hi_a = a.x_top_left, a.x_top_right
            lo_b, hi_b = b.x_bottom_left, b.x_bottom_right
        else:
            y = a.y_bottom
            lo_a, hi_a = a.x_bottom_left, a.x_bottom_right
            lo_b, hi_b = b.x_top_left, b.x_top_right
        lo, hi = max(lo_a, lo_b), min(hi_a, hi_b)
        if lo > hi:                       # no overlap: stay on a's own edge
            lo, hi = lo_a, hi_a
        pt = ((lo + hi) * 0.5, y)
        return (pt, (lo, hi, y)) if span else pt

    def _pull_corners(self, pts, spans, rounds=None):
        """Slide each crossing along its own edge toward the taut line.

        WHY THIS EXISTS, and it is a defect the operator felt before any
        instrument saw it (MOVECODE R5, 2026-08-28). `_shared_edge` answers
        the MIDPOINT of the interval two trapezoids share. That point is
        inside both -- which is all it ever claimed -- but it is not where a
        walker crosses. On map 280 trapezoid 531 borders the corridor 1921
        along x in [448, 3936]; a body standing at x = 3367 is 43 units from
        stepping straight north into it, and the midpoint rule sent it
        **1,176 units WEST** to x = 2192 first. Seven of R5's 34 routed
        clicks granted a first leg pointing away from the click (cos to
        -0.92, detours to 1.50x), and the operator's report was exactly
        that: "the second click would make me path back to the original
        position of the first click, then continue walking towards the
        second from there."

        `_string_pull` could not repair it: it only DROPS waypoints the
        previous one can already see, and here the corner after the midpoint
        is genuinely out of sight around real geometry, so the midpoint
        stayed. Dropping is not the same operation as sliding.

        The pass is Gauss-Seidel: for each interior crossing take the point
        on its own interval nearest the segment joining its neighbours, a
        few times over. Every candidate stays inside the interval, so it
        stays inside both trapezoids and the path stays as legal as the
        midpoint version was -- and route()'s per-segment clip() gate still
        has the last word. Endpoints never move. A crossing with no interval
        (a portal) is held fixed and simply anchors its neighbours.
        """
        # Read at CALL time, not as a default argument: a default binds at
        # definition and the A/B harness that tuned this silently compared the
        # pull against itself until that was caught (both arms "before" and
        # "after" printed the same 1-of-34, which is what a no-op looks like).
        if rounds is None:
            rounds = CORNER_PULL_ROUNDS
        if len(pts) < 3 or rounds <= 0:
            return pts
        pts = list(pts)
        for _ in range(rounds):
            moved = 0.0
            for i in range(1, len(pts) - 1):
                span = spans[i]
                if span is None:
                    continue
                lo, hi, y = span
                # Keep off the exact corner: the interval's ends are shared
                # with the NEXT trapezoid along, where a float boundary test
                # can fall either way (sec.1w's 1e-4 u excursions were this
                # class seen from the other side).
                inset = min(CORNER_PULL_INSET, (hi - lo) * 0.25)
                lo, hi = lo + inset, hi - inset
                if lo > hi:
                    lo = hi = (lo + hi) * 0.5
                ax, ay = pts[i - 1]
                bx, by = pts[i + 1]
                # The point on y that minimises |A->P| + |P->B|. Getting this
                # EXACTLY right is what keeps the pass monotone: the first
                # version used "the projection of the nearer endpoint" when
                # A and B sat on the same side, which is not the minimiser,
                # and it made 19 of 300 corpus paths LONGER while fixing the
                # backtrack. f(x) is convex, so clamping the unconstrained
                # optimum into the interval gives the constrained optimum.
                da, db = ay - y, by - y
                if da * db < 0.0:
                    # opposite sides: the straight line's own crossing
                    want = ax + (bx - ax) * (y - ay) / (by - ay)
                elif abs(da) < 1e-9 and abs(db) < 1e-9:
                    # both already on this line: any x between them is optimal
                    want = (ax + bx) * 0.5
                else:
                    # same side: reflect B across the line and cross to it
                    den = (2.0 * y - by) - ay
                    want = (ax if abs(den) < 1e-9
                            else ax + (bx - ax) * (y - ay) / den)
                nx = lo if want < lo else (hi if want > hi else want)
                moved = max(moved, abs(nx - pts[i][0]))
                pts[i] = (nx, y)
            if moved < CORNER_PULL_EPS:
                break
        return pts

    @staticmethod
    def _x_at(t, y):
        span = t.y_top - t.y_bottom
        f = 0.0 if span <= 0.0 else (y - t.y_bottom) / span
        return (t.x_bottom_left + f * (t.x_top_left - t.x_bottom_left),
                t.x_bottom_right + f * (t.x_top_right - t.x_bottom_right))

    def _overlap_point(self, a, b):
        lo = max(a.y_bottom, b.y_bottom)
        hi = min(a.y_top, b.y_top)
        if lo > hi:
            return b.centre
        y = (lo + hi) * 0.5
        al, ar = self._x_at(a, y)
        bl, br = self._x_at(b, y)
        left, right = max(al, bl), min(ar, br)
        if left > right:
            return b.centre
        return ((left + right) * 0.5, y)

    def _sightline(self, x0, y0, x1, y1, step=16.0):
        """(is every sample walkable, how many samples that took).

        THE SAMPLE SET IS EXACTLY clip()'s -- the same `n`, the same `f = k / n`,
        the same two multiply-adds -- so this answers exactly
        `clip(x0, y0, x1, y1) == (x1, y1)` and could be written that way. What
        differs is the ORDER the samples are asked in, and only for the segments
        that are going to be refused.

        clip() has to walk front to back because it returns HOW FAR you get. A
        yes/no question does not, and the smoother above asks nothing else. So
        this visits the midpoint first, then the quarter points, then the
        eighths -- every index in 1..n exactly once, coarsest first. A line that
        is walkable to the end costs exactly what it cost before; a line blocked
        somewhere in the middle is refuted in a handful of samples instead of
        after walking the whole way up to the wall. Most of the smoother's line
        tests are blocked ones -- it starts at the far end of the path and works
        back -- so this alone took the 1,500-route worst case from 336 ms to
        64.3.

        The order is a permutation, which is the part worth checking rather than
        believing: level `s` visits the ODD multiples of `s`, and over
        s = 2^k, 2^(k-1), ... 1 every index in 1..n is written exactly one way as
        odd * 2^v. test_pathmap.py asserts that against range(1, n+1) directly,
        and asserts the verdict against clip() on real segments, because a
        reordering that quietly DROPPED a sample would be faster and would
        happily approve a path through a wall.
        """
        dx, dy = x1 - x0, y1 - y0
        dist = (dx * dx + dy * dy) ** 0.5
        if dist <= 0.0:
            return True, 0            # clip() returns (x0, y0), which is (x1, y1)
        n = max(1, int(dist / step))
        walkable = self.walkable
        s = 1
        while s * 2 <= n:
            s *= 2
        spent = 0
        while s >= 1:
            k = s
            while k <= n:
                spent += 1
                f = k / n
                if not walkable(x0 + dx * f, y0 + dy * f):
                    return False, spent
                k += 2 * s
            s //= 2
        return True, spent

    def _visible(self, x0, y0, x1, y1):
        """`clip(x0, y0, x1, y1) == (x1, y1)`, without building the point.

        PLANE-BLIND, and no longer what the smoother uses to accept a
        shortcut: `_string_pull` asks this first (cheap, coarsest-first
        refutation) and then `_seam_walk` on the kept point's corridor plane
        (MOVECODE-1z-bb). §1z-ar recorded three desk attempts to measure the
        plane-blind pull's harm, the last refuted by its own control -- portal-
        linked trapezoids do NOT overlap in 2D -- and said not to add a plane
        term on a desk number. RUN-1zBA then measured it on a router grant: a
        body parked 7 s at a bridge's edge and a 2,021 u teleport (§1z-ba). The
        term that was added is a SEAM term, not the lead's any-plane-change
        clip; see SEAM_AWARE_ROUTE.
        """
        return self._sightline(x0, y0, x1, y1)[0]

    def _string_pull(self, pts, budget=None, planes=None):
        """Drop waypoints that the previous kept point can already reach.

        Uses the same sampling clip() does, so a segment survives only if every
        sample along it is walkable -- AND, given `planes` (the corridor plane
        per waypoint, MOVECODE-1z-bb), only if a body on the kept point's plane
        walks it without meeting a plane change no portal covers. The seam walk
        runs after the sightline and only on segments the sightline passed, so
        the refutation path costs what it cost before; its samples count
        against the same budget.

        THIS IS WHERE THE TIME WENT -- 94.2% of route(), against 3.5% for the
        A*. It is quadratic in waypoints and each of those tests is a line up to
        the length of the whole path: the worst pair in the chase-band sweep
        handed it 157 waypoints spanning 56,350 units, for two points 1,200
        units apart, and it spent 285 ms on them. The module header has the
        three measurements; `budget` is the only one of them that can change
        this function's answer, and PULL_SAMPLE_BUDGET says where it sits and
        why nothing measured reaches it.

        Out of budget, the loop takes pts[i + 1] every time and copies the rest
        of the A*'s own waypoints through. That is the un-smoothed path, which
        is longer and no less walkable -- route()'s final gate still has the
        last word on whether it goes out.
        """
        if budget is None:
            budget = PULL_SAMPLE_BUDGET
        seam = SEAM_AWARE_ROUTE and planes is not None
        out = [pts[0]]
        idx = [0]
        i = 0
        n = len(pts)
        spent = 0
        while i < n - 1:
            j = n - 1
            while j > i + 1:
                if spent >= budget:
                    j = i + 1               # stop shortening; keep walking
                    break
                ok, used = self._sightline(*out[-1], *pts[j])
                spent += used
                if ok and seam and planes[i] is not None:
                    # At the sightline's own step, off-mesh-tolerant: this
                    # asks only whether the shortcut crosses a blind seam.
                    # The 2 u strict walk is route()'s gate, after the pull.
                    stop, used = self._seam_walk(out[-1][0], out[-1][1],
                                                 pts[j][0], pts[j][1],
                                                 planes[i], 16.0, strict=False)
                    spent += used
                    ok = stop == pts[j]
                if ok:
                    break
                j -= 1
            out.append(pts[j])
            idx.append(j)
            i = j
        # WHICH waypoints survived, by index, for route()'s plane bookkeeping.
        # Value-matching cannot recover it: a portal crossing puts two or three
        # COINCIDENT waypoints in the corridor (the edge onto the portal line,
        # the crossing, the edge off it) on DIFFERENT planes, the pull keeps
        # the farthest of them, and the first-match walk handed route()'s gate
        # the plane of the first -- which refused a leg the pull had accepted
        # on the right plane (test_pathmap.py section 14's U-turn came back
        # None). `with_planes` had been reporting that wrong plane too.
        self._pull_idx = idx
        return out

    # -- loading ---------------------------------------------------------

    @classmethod
    def from_chunk(cls, blob):
        sig, version, _unknown = struct.unpack_from("<III", blob, 0)
        if sig != SIGNATURE:
            raise ValueError(f"pathing signature 0x{sig:08X} != "
                             f"0x{SIGNATURE:08X}")
        if version != VERSION:
            raise ValueError(f"pathing version {version} != {VERSION}")

        records, p = {}, 12
        while p + 5 <= len(blob):
            tag = blob[p]
            size, = struct.unpack_from("<I", blob, p + 1)
            records[tag] = (p + 5, size)
            p += 5 + size
            if tag == TERMINATOR:
                break
        if p != len(blob):
            raise ValueError(f"tag walk ended at {p} of {len(blob)} bytes")
        if TAG_PLANES not in records:
            raise ValueError("no tag 8 (planes) in pathing chunk")

        off, size = records[TAG_PLANES]
        pay = memoryview(blob)[off:off + size]
        count, = struct.unpack_from("<I", pay, 0)

        trapezoids, planes, portals, portal_traps, p = [], [], [], [], 4
        for pi in range(count):
            header = None
            for want, field, esz in PLANE_LAYOUT:
                if p + 5 > len(pay):
                    raise ValueError(f"plane {pi}: payload ends at {p}")
                tag = pay[p]
                declared, = struct.unpack_from("<I", pay, p + 1)
                body = p + 5
                if tag != want:
                    raise ValueError(f"plane {pi}: expected tag {want}, "
                                     f"got {tag} at {p}")
                if want == 0:
                    header = dict(zip(PLANE_HEADER_FIELDS,
                                      struct.unpack_from("<8I", pay, body)))
                    length = declared
                elif esz is None:
                    length = declared
                else:
                    # Counts win. Tag 11 declares double what it stores.
                    length = header[field] * esz
                if want == 2:
                    for i in range(header["trapezoids"]):
                        (ntl, ntr, nbl, nbr, pl, pr,
                         yt, yb, xtl, xtr, xbl, xbr) = \
                            TRAPEZOID.unpack_from(pay, body + TRAPEZOID_SIZE * i)
                        trapezoids.append(
                            Trapezoid(pi, i, yt, yb, xtl, xtr, xbl, xbr,
                                      (ntl, ntr, nbl, nbr), pl, pr))
                elif want == 10 and header["portalTraps"]:
                    portal_traps.append(list(struct.unpack_from(
                        f"<{header['portalTraps']}I", pay, body)))
                elif want == 10:
                    portal_traps.append([])
                elif want == 9:
                    row = []
                    for i in range(header["portals"]):
                        o = body + PORTAL_SIZE * i
                        traps, offset, neigh, unknown = \
                            struct.unpack_from("<4H", pay, o)
                        row.append(Portal(pi, i, traps, offset, neigh,
                                          unknown, pay[o + 8]))
                    portals.append(row)
                p = body + length
            planes.append(header)
        if p != len(pay):
            raise ValueError(f"plane walk ended at {p} of {len(pay)} bytes")
        return cls(trapezoids, planes, portals, portal_traps)

    @classmethod
    def load(cls, map_file_id, archive=None, table=None):
        """Open a map by the id a server hands the client."""
        own = archive is None
        ar = archive or Archive()
        try:
            table = table if table is not None else file_id_table(ar)
            row = table.get(map_file_id)
            if row is None:
                raise KeyError(f"no file id 0x{map_file_id:X} in the archive")
            entry = ar.row(row)
            data = ar.read(entry)
            for chunk_id, off, size in ffna_chunks(data):
                if chunk_id == PATHING_CHUNK:
                    return cls.from_chunk(bytes(data[off:off + size]))
            raise ValueError(f"file id 0x{map_file_id:X} (row {row}) has no "
                             f"pathing chunk")
        finally:
            if own:
                ar.close()


if __name__ == "__main__":
    KAMADAN = 0x345CC
    fid = int(sys.argv[1], 0) if len(sys.argv) > 1 else KAMADAN
    import time
    t0 = time.perf_counter()
    pm = PathingMap.load(fid)
    dt = time.perf_counter() - t0
    xs = [v for t in pm.trapezoids
          for v in (t.x_top_left, t.x_top_right,
                    t.x_bottom_left, t.x_bottom_right)]
    ys = [v for t in pm.trapezoids for v in (t.y_top, t.y_bottom)]
    print(f"file id 0x{fid:X}: {len(pm.planes)} planes, "
          f"{len(pm.trapezoids)} trapezoids, loaded in {dt:.2f}s")
    print(f"  extent x {min(xs):.0f}..{max(xs):.0f}  y {min(ys):.0f}..{max(ys):.0f}")
