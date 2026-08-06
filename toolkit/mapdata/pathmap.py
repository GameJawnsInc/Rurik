"""Walkable geometry: the navmesh a Guild Wars map carries in its pathing chunk.

This is what lets a server answer "is this point walkable" instead of letting a
character walk through walls. The client already refuses to render you through a
wall; without this the server disagrees with it and drags you back or shoves you
through.

WHERE THE LAYOUT COMES FROM. The struct names below are GuildWarsMapBrowser's
ImHex pattern (FFNA_ImHexPatterns/gw_file_pattern_complete.hexpat). That is ONE
lineage -- the Jonathan-Greve and gwdevhub repositories are a fork pair, so
agreement between them is not corroboration -- and it has no test or fixture. It
is a hypothesis, not a spec.

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

    # -- queries ---------------------------------------------------------

    def containing(self, x, y):
        """Every trapezoid holding this point. Usually zero or one."""
        return [t for t in self._bands.get(int(y // BAND), ())
                if t.contains(x, y)]

    def walkable(self, x, y):
        for t in self._bands.get(int(y // BAND), ()):
            if t.contains(x, y):
                return True
        return False

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

    def clip(self, x0, y0, x1, y1, step=16.0):
        """How far along (x0,y0)->(x1,y1) a character can actually get.

        Returns the last sampled point that is walkable, or the start if the
        very first step is not. Sampling, not solving: a gap narrower than
        `step` can be stepped over. 16 units is about a twentieth of a second at
        run speed, and the client does its own collision besides.
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

    def route(self, x0, y0, x1, y1):
        """A walkable path from start to goal, or None if there is not one.

        A* over the trapezoid adjacency graph, then a string-pulling pass that
        drops any waypoint the previous one can already see. The result is a
        list of points beginning at the start and ending at the goal; walking
        it in straight segments never leaves the navmesh.

        SAME PLANE ONLY, and it says None rather than guessing otherwise.
        Crossing planes needs a rule for pairing a portal's trapezoids with its
        neighbour's, and the field that would most obviously carry it is the one
        the Portal class records as refuted. There is also no height in this
        file, so a wrong cross-plane link would route a player through a bridge
        rather than over it -- a silent, plausible-looking error of exactly the
        kind this project refuses to ship.
        """
        starts = self.containing(x0, y0)
        goals = self.containing(x1, y1)
        if not starts or not goals:
            return None
        goal_set = {self._flat_index(g) for g in goals}
        start = starts[0]
        si = self._flat_index(start)
        if si in goal_set:
            return [(x0, y0), (x1, y1)]
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
        for a, b in zip(chain, chain[1:]):
            pts.append(self._shared_edge(self.trapezoids[a],
                                         self.trapezoids[b]))
        pts.append((x1, y1))
        path = self._string_pull(pts)
        # Last gate, and it is not belt-and-braces. A cross-plane step joins two
        # trapezoids that the file says share a crossing; where they do not also
        # overlap in (x, y) -- about a fifth of them in Pre-Searing -- the
        # waypoint falls back to the far trapezoid's centre and the straight line
        # to it can leave the mesh. Returning nothing is a worse answer than a
        # detour and a better one than a path through a wall.
        for a, b in zip(path, path[1:]):
            if self.clip(*a, *b) != b:
                return None
        return path

    def _shared_edge(self, a, b):
        """A point on the edge `a` and `b` share, inside both.

        Across a portal the two trapezoids are the same physical place on two
        planes rather than neighbours on one, so there is no shared edge; the
        centre of where they overlap is inside both.
        """
        if a.plane != b.plane:
            return self._overlap_point(a, b)
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
        return ((lo + hi) * 0.5, y)

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

    def _string_pull(self, pts):
        """Drop waypoints that the previous kept point can already reach.

        Uses the same sampling clip() does, so a segment survives only if every
        sample along it is walkable.
        """
        out = [pts[0]]
        i = 0
        while i < len(pts) - 1:
            j = len(pts) - 1
            while j > i + 1:
                if self.clip(*out[-1], *pts[j]) == pts[j]:
                    break
                j -= 1
            out.append(pts[j])
            i = j
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
            entry = ar.entries[row - 1]
            if entry.index != row:
                entry = next(e for e in ar.entries if e.index == row)
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
