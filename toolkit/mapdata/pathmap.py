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

WHAT IS NOT DECODED. Portals, x/y BSP nodes, sink nodes and edge vectors are
read as sized blocks and skipped. They are the pathfinding graph -- what you
need to route AROUND an obstacle. Collision does not need them.

THERE IS NO HEIGHT. Planes are not elevations in any units we can read; nothing
in the file says what z a plane sits at, and GWToolbox fabricates one on load.
walkable() therefore asks "walkable on ANY plane", which is right for flat
ground and wrong under a bridge. Said plainly because it will matter later.
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


class Trapezoid:
    """One walkable quad: a y span whose left and right edges are lines.

    Field names are the source's. The geometry is ours to check, and does.
    """

    __slots__ = ("plane", "index", "y_top", "y_bottom",
                 "x_top_left", "x_top_right", "x_bottom_left", "x_bottom_right")

    def __init__(self, plane, index, y_top, y_bottom,
                 x_top_left, x_top_right, x_bottom_left, x_bottom_right):
        self.plane = plane
        self.index = index
        self.y_top = y_top
        self.y_bottom = y_bottom
        self.x_top_left = x_top_left
        self.x_top_right = x_top_right
        self.x_bottom_left = x_bottom_left
        self.x_bottom_right = x_bottom_right

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

    def __init__(self, trapezoids, planes):
        self.trapezoids = trapezoids
        self.planes = planes
        self._bands = {}
        for t in trapezoids:
            lo = int(t.y_bottom // BAND)
            hi = int(t.y_top // BAND)
            for b in range(lo, hi + 1):
                self._bands.setdefault(b, []).append(t)

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

        trapezoids, planes, p = [], [], 4
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
                        (_ntl, _ntr, _nbl, _nbr, _pl, _pr,
                         yt, yb, xtl, xtr, xbl, xbr) = \
                            TRAPEZOID.unpack_from(pay, body + TRAPEZOID_SIZE * i)
                        trapezoids.append(
                            Trapezoid(pi, i, yt, yb, xtl, xtr, xbl, xbr))
                p = body + length
            planes.append(header)
        if p != len(pay):
            raise ValueError(f"plane walk ended at {p} of {len(pay)} bytes")
        return cls(trapezoids, planes)

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
