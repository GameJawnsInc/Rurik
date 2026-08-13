"""Check the navmesh reader against real bytes.

The layout under test came from ONE source lineage with no fixture of its own
(see the header of pathmap.py), so these checks are the only thing standing
between "GuildWarsMapBrowser says so" and a server that refuses to let a player
walk where the game allows it.

Three of them can fail for the right reason:

  * Section 2 walks 39 planes of ten sub-records through tag 8 and requires the
    walk to end on the exact final byte. Every element size participates. This
    is the same shape of argument as the chunk-table check in test_archive.py --
    an independent structure that either consumes the block exactly or does not.
  * Section 3 asks the geometry whether it is geometry. Inverted y spans and
    crossed x edges are what a misread struct produces, and the count should be
    zero, not small.
  * Section 5 runs the walk across a sample of the whole map corpus, so a layout
    that happens to fit Kamadan and nothing else is caught.

SECTION 10 IS A DIFFERENT KIND OF CHECK and is worth its own note, because a
router is the one thing here that can be WRONG AND LOOK RIGHT. route() runs on
the thread that owns the world, on a 50 ms tick, and before 2026-08-13 its worst
case in the band a hostile chases in was 336 ms -- 6.6 tick periods, 11 routes in
1,500 over a whole tick, and an intermittent world freeze nobody could attribute.
That is fixed, and the measurement is repeated here rather than quoted.

The trap in checking it is that a router which quietly returns None, or returns a
path through a wall, is FASTER. So the latency number is the least of what
section 10 asserts, and never appears without four things beside it:

  * every path returned passes route()'s own consecutive-clip validity gate, over
    the whole 1,500-pair set rather than a sample;
  * the None rate is measured BEFORE and AFTER on the same pairs and must be
    equal -- a smoother that gives up is the expected failure mode;
  * path length is compared before and after, mean and worst case;
  * the sabotage is BUILT AND RUN: a route() that returns the raw unsmoothed A*
    path is faster than the real one (max 11.6 ms against 17.9) and PASSES the
    timing check, so if the length check did not go red -- it does, at a mean
    ratio of 2.80 and a worst of 52.6 -- there would be no check here at all.

The pre-fix walkable(), _string_pull() and component pre-check are reconstructed
in this file so BEFORE and AFTER are two live answers in one process, the way
test_codescan.py's §8 reproduces the old grouping inline. A number copied out of
a session log is not a control.

    python toolkit/mapdata/test_pathmap.py
    python toolkit/mapdata/test_pathmap.py --sample 60
    python toolkit/mapdata/test_pathmap.py --routes 400   # a quicker section 10
    python toolkit/mapdata/test_pathmap.py --all      # every map, minutes

MEASURED VALUES ARE KAMADAN'S, on the archive our patched client has run. A
different Gw.dat is fine -- the file id is a content key -- but if that map ever
changes shape these numbers are the alarm.
"""

import argparse
import math
import os
import random
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import (Archive, ffna_chunks, file_id_table,  # noqa: E402
                     DEFAULT_DAT, FILE_ID_HIGH_BIT)
import pathmap  # noqa: E402
from pathmap import (PathingMap, PATHING_CHUNK, SIGNATURE, VERSION,  # noqa: E402
                     TRAPEZOID_SIZE, NO_NEIGHBOUR, NO_PORTAL, BAND)
import checks  # noqa: E402

KAMADAN_FILE_ID = 0x345CC
KAMADAN_ROW = 22371
KAMADAN_CHUNK_BYTES = 199130
KAMADAN_PLANES = 39
KAMADAN_TRAPEZOIDS = 1270

# OpenTyria's static spawn for Kamadan. It was never checked against anything
# until this file; section 4 is that check.
KAMADAN_SPAWN = (-9067.0, 13218.0)

# The two map file ids the archive stores with bit 31 set. An exact-match lookup
# misses both, which is why the Pre-Searing region was written off as
# unreachable; section 6 is the regression guard on that.
PRESEARING_FILE_ID = 0x1B97D
PRESEARING_ROW = 7982
PRESEARING_PLANES = 58
PRESEARING_TRAPEZOIDS = 6120
NORTHLANDS_FILE_ID = 0x1C539
NORTHLANDS_ROW = 20118
HIGH_BIT_IDS = 25
MEASURED_ENTRY_COUNT = 177342

ROUTE_SAMPLE = 60

MAP_FLAGS = 259

# -- section 10: the chase band ------------------------------------------
# The band enemy_move_tick actually chases in, straight out of authsrv.py:
# ENEMY_MELEE_RANGE (150) is where a hostile stops walking and starts swinging,
# AGGRO_RANGE (1200) is where it notices you at all. Routes outside it are not
# the ones that can freeze the world, so measuring them would flatter the
# result. Duplicated rather than imported: toolkit/mapdata must not grow a
# dependency on the server, and if the server's numbers ever move, this file
# saying 150..1200 out loud is what makes the divergence findable.
CHASE_LO, CHASE_HI = 150.0, 1200.0
TICK_MS = 50.0                 # authsrv.TICK_SECONDS, the world's whole budget
TAIL_ROUTES = 1500

# The tolerances section 10 holds the smoother to. The fix as shipped is
# answer-identical, so the MEASURED values are 1.000000 and 1.000000 -- these
# are headroom for a future bounded smoother, not a description of today. They
# are set where the raw-unsmoothed sabotage (mean 2.80, worst 52.6) still goes
# red by a wide margin, because a tolerance that the sabotage slips through is
# not a tolerance.
LENGTH_MEAN_MAX = 1.01
LENGTH_WORST_MAX = 1.25


def old_walkable(pm, x, y):
    """walkable() as it stood before 2026-08-13: a y band of Trapezoid objects.

    Reconstructed here, not described, so "5.82 us against 1.23" and "336 ms
    against 17.9" are differences between two answers this process computed.
    """
    for t in pm._bands.get(int(y // BAND), ()):
        if t.contains(x, y):
            return True
    return False


def old_string_pull(pm, pts):
    """_string_pull() as it stood before 2026-08-13: unbounded, clip() in order."""
    out = [pts[0]]
    i = 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1:
            if pm.clip(*out[-1], *pts[j]) == pts[j]:
                break
            j -= 1
        out.append(pts[j])
        i = j
    return out


class as_before:
    """Context manager putting a PathingMap back to its pre-fix behaviour.

    Three instance attributes are the whole difference, which is worth saying
    out loud: route() itself gained only the component pre-check, and giving
    every trapezoid the same component root makes that branch inert rather than
    needing a second copy of the function. So the BEFORE run below exercises the
    SAME route() body -- what changed is the three primitives underneath it.
    """

    def __init__(self, pm):
        self.pm = pm

    def __enter__(self):
        pm = self.pm
        self.saved = pm._component
        pm.walkable = lambda x, y: old_walkable(pm, x, y)
        pm._string_pull = lambda pts, budget=None: old_string_pull(pm, pts)
        pm._component = [0] * len(pm.trapezoids)
        return pm

    def __exit__(self, *exc):
        pm = self.pm
        del pm.walkable
        del pm._string_pull
        pm._component = self.saved
        return False


def chase_pairs(pm, n, seed=8):
    """n (start, goal) pairs, both walkable, CHASE_LO..CHASE_HI apart.

    Starts are trapezoid centres so a start is always inside the mesh; goals are
    thrown at a random bearing and kept only if they land on walkable ground,
    which is what makes the set a mixture of clear lines, detours around
    obstacles and goals in another component.
    """
    rng = random.Random(seed)
    pairs = []
    guard = 0
    while len(pairs) < n and guard < n * 400:
        guard += 1
        ax, ay = rng.choice(pm.trapezoids).centre
        if not pm.walkable(ax, ay):
            continue
        ang = rng.uniform(0.0, 2.0 * math.pi)
        d = rng.uniform(CHASE_LO, CHASE_HI)
        bx, by = ax + math.cos(ang) * d, ay + math.sin(ang) * d
        if not pm.walkable(bx, by):
            continue
        pairs.append((ax, ay, bx, by))
    return pairs


def sweep(pm, pairs):
    """Route every pair, timing each one. Returns (milliseconds, paths)."""
    ms, paths = [], []
    for (ax, ay, bx, by) in pairs:
        t0 = time.perf_counter()
        p = pm.route(ax, ay, bx, by)
        ms.append((time.perf_counter() - t0) * 1000.0)
        paths.append(p)
    return ms, paths


def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def confirmed_over_tick(pm, pairs, ms, repeats=5):
    """The routes that REALLY cost more than a tick, re-timed best of N.

    One timing on a shared machine measures the computation and whatever else
    the box was doing. That is not a hypothetical here: this file was first run
    green at max 17.9 ms and then read 52.4 ms on the same code half an hour
    later, with four other agents' suites running in the same worktree and the
    median at 0.306 ms against an idle 0.16. A check that reddens because
    another process woke up is worse than no check, because the next person
    lowers the threshold rather than reading it.

    The minimum over repeats is the standard estimator for the cost of the work
    rather than the cost of the day: a route that genuinely spends 300 ms of CPU
    spends it every time, and a scheduling hiccup does not survive a second
    look. Only the candidates are re-timed, so a run with nothing over the tick
    pays nothing at all -- and the estimator only ever moves a number DOWN, so
    it can hide a slow route only by hiding one that is not reliably slow.
    """
    out = []
    for k, v in enumerate(ms):
        if v <= TICK_MS:
            continue
        ax, ay, bx, by = pairs[k]
        best = min(_time_one(pm, ax, ay, bx, by) for _ in range(repeats))
        if best > TICK_MS:
            out.append((k, best))
    return out


def _time_one(pm, ax, ay, bx, by):
    t0 = time.perf_counter()
    pm.route(ax, ay, bx, by)
    return (time.perf_counter() - t0) * 1000.0


def latency_table(label, ms):
    """Print the percentile table and return how many blew a whole tick."""
    over = sum(1 for v in ms if v > TICK_MS)
    print(f"      {label:<8} p50 {pct(ms, .5):7.3f}  p90 {pct(ms, .9):7.3f}  "
          f"p99 {pct(ms, .99):7.3f}  p99.9 {pct(ms, .999):8.3f}  "
          f"max {max(ms):8.3f} ms = {max(ms) / TICK_MS:.2f} ticks, "
          f"{over} over a tick, {sum(ms) / 1000.0:.2f} s total")
    return over


def path_length(p):
    return sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))


def length_ratios(base, other):
    """Length of `other`'s path over `base`'s, for the pairs both routed."""
    out = []
    for a, b in zip(base, other):
        if a and b and path_length(a) > 0.0:
            out.append(path_length(b) / path_length(a))
    return out


def all_valid(pm, paths):
    """How many returned paths fail route()'s own consecutive-clip gate.

    Deliberately re-run through clip() rather than through _visible(): clip()
    walks front to back and is the implementation _sightline() was derived
    FROM, so a defect in the reordering cannot hide behind itself here.
    """
    bad = 0
    for p in paths:
        if not p:
            continue
        if any(pm.clip(*p[i], *p[i + 1]) != p[i + 1] for i in range(len(p) - 1)):
            bad += 1
    return bad

# FLOOR: 62 -- the checks that run on any Gw.dat, whatever --sample, --routes or
# --all is asked for. MEASURED on the run-dir archive, 2026-08-13: a green
# default run prints 64, and the two above the floor are the "row is the
# measured one" checks in section 6, which turn into declared skips on an
# archive with a different entry count. Everything else here is unconditional:
# 6 in section 1, 5 in section 2, 3 in section 3, 4 in section 4, 1 in section 5
# (the sample size changes how many maps that one check walks, not how many
# checks run), 8 of section 6's 10, 3 in section 7, 6 in section 8, 5 in
# section 9, and 21 in section 10 (3 + 2 + 2 + 2 + 6 + 2 + 4 across its parts
# a to g) -- `--routes` likewise changes the sample, not the count.
# Was 41 against a green 43 before section 10 existed.
# If a run scores 61, a section stopped executing and the passes above it are
# not evidence of anything.
LEDGER = checks.Ledger("pathing map", floor=62)
check = checks.adopt(LEDGER)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--sample", type=int, default=25,
                    help="how many maps to walk in section 5")
    ap.add_argument("--routes", type=int, default=TAIL_ROUTES,
                    help="how many chase-band routes section 10 times")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    t0 = time.perf_counter()
    with Archive(args.dat) as ar:
        table = file_id_table(ar)

        # -- 1. the chunk itself ----------------------------------------
        print("\n1. Kamadan's pathing chunk")
        row = table.get(KAMADAN_FILE_ID)
        check(row == KAMADAN_ROW, "file id resolves to the reference row",
              f"0x{KAMADAN_FILE_ID:X} -> {row}")
        entry = next(e for e in ar.entries if e.index == row)
        check(entry.flags == MAP_FLAGS, "the row carries map flags",
              f"flags {entry.flags}")
        data = ar.read(entry)
        blob = None
        for cid, off, size in ffna_chunks(data):
            if cid == PATHING_CHUNK:
                blob = bytes(data[off:off + size])
                break
        check(blob is not None, "map file has a pathing chunk")
        check(len(blob) == KAMADAN_CHUNK_BYTES, "chunk is the measured size",
              f"{len(blob)} bytes")
        sig, ver, _ = struct.unpack_from("<III", blob, 0)
        check(sig == SIGNATURE, "signature matches", f"0x{sig:08X}")
        check(ver == VERSION, "version matches", f"{ver}")

        # -- 2. the walk ends exactly ------------------------------------
        print("\n2. Tag walk consumes the chunk to the byte")
        pm = PathingMap.from_chunk(blob)      # raises if either walk misses
        check(True, "top-level and plane walks both landed on the end")
        check(len(pm.planes) == KAMADAN_PLANES, "plane count",
              f"{len(pm.planes)}")
        check(len(pm.trapezoids) == KAMADAN_TRAPEZOIDS, "trapezoid count",
              f"{len(pm.trapezoids)}")
        check(TRAPEZOID_SIZE == 44, "trapezoid record is 44 bytes")
        total = sum(p["trapezoids"] for p in pm.planes)
        check(total == len(pm.trapezoids),
              "header counts agree with what was decoded", f"{total}")

        # -- 3. the geometry is geometry ---------------------------------
        print("\n3. Trapezoids are well formed")
        bad_y = [t for t in pm.trapezoids if t.y_top < t.y_bottom]
        bad_x = [t for t in pm.trapezoids
                 if t.x_top_left > t.x_top_right
                 or t.x_bottom_left > t.x_bottom_right]
        check(not bad_y, "no inverted y spans", f"{len(bad_y)} bad")
        check(not bad_x, "no crossed x edges", f"{len(bad_x)} bad")
        xs = [v for t in pm.trapezoids
              for v in (t.x_top_left, t.x_top_right,
                        t.x_bottom_left, t.x_bottom_right)]
        ys = [v for t in pm.trapezoids for v in (t.y_top, t.y_bottom)]
        span = max(xs) - min(xs), max(ys) - min(ys)
        check(1000.0 < span[0] < 1e6 and 1000.0 < span[1] < 1e6,
              "extent is a plausible map size",
              f"x {min(xs):.0f}..{max(xs):.0f}  y {min(ys):.0f}..{max(ys):.0f}")

        # -- 4. the spawn point ------------------------------------------
        print("\n4. The spawn our server already used")
        hits = pm.containing(*KAMADAN_SPAWN)
        check(len(hits) == 1, "spawn is inside exactly one trapezoid",
              f"{len(hits)} hit(s)")
        far = (min(xs) - 5000.0, min(ys) - 5000.0)
        check(not pm.walkable(*far), "a point well outside the map is not walkable")
        # A clip that starts walkable and aims off the map must stop somewhere
        # short of the target, and must stay walkable.
        end = pm.clip(KAMADAN_SPAWN[0], KAMADAN_SPAWN[1], far[0], far[1])
        check(end != far, "clip refuses to reach an unwalkable target")
        check(pm.walkable(*end), "clip's stopping point is itself walkable",
              f"({end[0]:.0f}, {end[1]:.0f})")

        # -- 5. the rest of the corpus -----------------------------------
        rows = [e for e in ar.entries if e.flags == MAP_FLAGS]
        picks = rows if args.all else rows[::max(1, len(rows) // args.sample)]
        print(f"\n5. Plane walk across {len(picks)} of {len(rows)} maps")
        walked = skipped = 0
        broke = []
        for e in picks:
            try:
                d = ar.read(e)
                chunk = None
                for cid, off, size in ffna_chunks(d):
                    if cid == PATHING_CHUNK:
                        chunk = bytes(d[off:off + size])
                        break
                if chunk is None:
                    skipped += 1
                    continue
                m = PathingMap.from_chunk(chunk)
                if any(t.y_top < t.y_bottom for t in m.trapezoids):
                    broke.append((e.index, "inverted y"))
                else:
                    walked += 1
            except Exception as exc:                      # noqa: BLE001
                broke.append((e.index, str(exc)[:70]))
        check(not broke, f"every sampled map walks exactly",
              f"{walked} walked, {skipped} without a pathing chunk")
        for row_i, why in broke[:6]:
            print(f"        row {row_i}: {why}")

        # -- 6. the maps behind the bit-31 ids ---------------------------
        # These fail loudly if file_id_table() ever goes back to an
        # exact-match lookup: the id a server sends is the masked form and
        # only the raw form is in the table.
        print("\n6. The file ids stored with bit 31 set")
        raw = struct.unpack_from(
            f"<{(len(ar.read(ar.entries[1])) // 8) * 2}I", ar.read(ar.entries[1]))
        stored = {raw[i * 2] for i in range(len(raw) // 2)}
        high = {f for f in stored if f & FILE_ID_HIGH_BIT}
        check(len(high) == HIGH_BIT_IDS, "the high-bit id census is unchanged",
              f"{len(high)} ids")
        # The invariant the mask-on-miss lookup depends on: no bit-31 id's
        # masked form is also a real id, so the two can never compete.
        shadowed = {f & ~FILE_ID_HIGH_BIT for f in high} & stored
        check(not shadowed, "no masked form collides with a real file id",
              f"{len(shadowed)} collision(s)")

        for label, fid, want_row in (
                ("Pre-Searing", PRESEARING_FILE_ID, PRESEARING_ROW),
                ("The Northlands", NORTHLANDS_FILE_ID, NORTHLANDS_ROW)):
            got = table.get(fid)
            check(got is not None, f"{label} id resolves at all",
                  f"0x{fid:X} -> {got}")
            if got is None:
                continue
            check(table.get(fid | FILE_ID_HIGH_BIT) == got,
                  f"{label} raw and masked ids agree")
            e = next(x for x in ar.entries if x.index == got)
            check(e.flags == MAP_FLAGS, f"{label} row carries map flags",
                  f"flags {e.flags}")
            if ar.entry_count == MEASURED_ENTRY_COUNT:
                check(got == want_row, f"{label} row is the measured one",
                      f"{got}")
            else:
                LEDGER.skip(f"{label} row index",
                            f"archive has {ar.entry_count} entries, "
                            f"measured on {MEASURED_ENTRY_COUNT}")

        # -- 7. the routing graph ----------------------------------------
        # The adjacency check is the strongest thing in this file. Four
        # indices read out of one 44-byte record are checked against four
        # read out of a different record, and upstream's TL/TR/BL/BR naming
        # additionally predicts WHICH of the four answers. Nothing in our
        # decoder can force that.
        print("\n7. the trapezoid routing graph")
        links = sym = opposite = oor = 0
        for t in pm.trapezoids:
            here = [x for x in pm.trapezoids if x.plane == t.plane]
            for slot, n in enumerate(t.neighbours):
                if n == NO_NEIGHBOUR:
                    continue
                links += 1
                if n >= len(here):
                    oor += 1
                    continue
                other = here[n]
                if t.index in other.neighbours:
                    sym += 1
                want = (2, 3) if slot < 2 else (0, 1)
                if t.index in (other.neighbours[want[0]],
                               other.neighbours[want[1]]):
                    opposite += 1
        check(oor == 0, "every neighbour index is in range", f"{links} links")
        check(sym == links, "adjacency is symmetric", f"{sym}/{links}")
        check(opposite == links,
              "a top-edge link is answered across the bottom edge",
              f"{opposite}/{links}")

        print("\n8. portals")
        total_portals = sum(len(r) for r in pm.portals)
        bad_plane = sum(1 for r in pm.portals for p in r
                        if p.neighbour >= len(pm.planes))
        check(bad_plane == 0, "every portal names a plane that exists",
              f"{total_portals} portals")
        partition_ok = 0
        for pi, row in enumerate(pm.portals):
            traps = pm.portal_traps[pi]
            cover = [0] * len(traps)
            for p in row:
                for k in range(p.offset, min(p.offset + p.traps, len(cover))):
                    cover[k] += 1
            if all(c == 1 for c in cover):
                partition_ok += 1
        check(partition_ok == len(pm.portals),
              "portal slices partition each plane's portalTraps exactly",
              f"{partition_ok}/{len(pm.portals)} planes")
        # Reciprocity of the plane relation, the same argument as adjacency.
        names = {pi: {p.neighbour for p in row}
                 for pi, row in enumerate(pm.portals)}
        rel = [(a, b) for a, s in names.items() for b in s]
        recip = sum(1 for a, b in rel if a in names.get(b, ()))
        check(recip == len(rel), "the plane-to-plane relation is reciprocal",
              f"{recip}/{len(rel)}")
        # The pairing, and the reason cross-plane routing is a decode rather
        # than a heuristic: exactly two portals share a pair id, never one or
        # three, and the partner is always across the boundary named.
        groups = {}
        for row in pm.portals:
            for p_ in row:
                groups.setdefault(p_.pair_id, []).append(p_)
        sizes = {len(v) for v in groups.values()}
        check(sizes == {2}, "every pair id is shared by exactly two portals",
              f"group sizes {sorted(sizes)}, {len(groups)} pairs")
        crossed = sum(1 for v in groups.values() if len(v) == 2
                      and v[0].plane == v[1].neighbour
                      and v[1].plane == v[0].neighbour)
        check(crossed == len(groups),
              "each pair spans the planes its two halves name",
              f"{crossed}/{len(groups)}")
        # ArenaNet's own assert, from PathDir.cpp.
        stray = 0
        for t in pm.trapezoids:
            n = len(pm.portals[t.plane])
            for k in (t.portal_left, t.portal_right):
                if k != NO_PORTAL and k >= n:
                    stray += 1
        check(stray == 0,
              "m_trapezoid->portalLeft/Right < pathMap.portalCount",
              "the client's own invariant")

        print("\n9. routing finds walkable paths around obstacles")
        random.seed(7)
        pool = pm.trapezoids
        blocked = routed = clean = 0
        for _ in range(60000):
            a, b = random.choice(pool), random.choice(pool)
            ax, ay = a.centre
            bx, by = b.centre
            if pm.clip(ax, ay, bx, by) == (bx, by):
                continue                      # straight line already works
            blocked += 1
            path = pm.route(ax, ay, bx, by)
            if path:
                routed += 1
                if all(pm.clip(*path[i], *path[i + 1]) == path[i + 1]
                       for i in range(len(path) - 1)):
                    clean += 1
            if blocked >= ROUTE_SAMPLE:
                break
        check(routed > blocked // 2, "most blocked pairs are routable",
              f"{routed} of {blocked} sampled")
        # The load-bearing one: a path we return must be walkable end to end.
        # Returning nothing is allowed -- planes are fragmented without the
        # cross-plane links -- but returning a path through a wall is not.
        check(clean == routed, "EVERY returned path is walkable end to end",
              f"{clean}/{routed}")

        pre = PathingMap.load(PRESEARING_FILE_ID, archive=ar, table=table)
        check(len(pre.planes) == PRESEARING_PLANES, "Pre-Searing plane count",
              f"{len(pre.planes)}")
        check(len(pre.trapezoids) == PRESEARING_TRAPEZOIDS,
              "Pre-Searing trapezoid count", f"{len(pre.trapezoids)}")
        bad = [t for t in pre.trapezoids
               if t.y_top < t.y_bottom
               or t.x_top_left > t.x_top_right
               or t.x_bottom_left > t.x_bottom_right]
        check(not bad, "Pre-Searing trapezoids are well formed",
              f"{len(bad)} malformed")

        # -- 10. the routing tail ----------------------------------------
        # Pre-Searing rather than Kamadan on purpose: 6,120 trapezoids in 15
        # components against 1,270 in 4, so it is the map where the smoother
        # blew a tick and where a failed search is expensive. Kamadan never
        # exceeded 35 ms even before the fix.
        print("\n10. route() latency in the chase band")

        # (a) the reordered line test asks EXACTLY clip()'s samples. The whole
        #     saving is that a blocked line is refused early, and the cheapest
        #     way to be "fast" would be to look at fewer points -- which would
        #     approve a path through a wall. So capture what each one asks and
        #     compare the sets, on a segment that is walkable end to end (a
        #     blocked one stops both early and proves nothing).
        seg = None
        rng10 = random.Random(21)
        for _ in range(4000):
            ax, ay = rng10.choice(pre.trapezoids).centre
            ang, d = rng10.uniform(0, 2 * math.pi), rng10.uniform(300.0, 900.0)
            bx, by = ax + math.cos(ang) * d, ay + math.sin(ang) * d
            if pre.clip(ax, ay, bx, by) == (bx, by):
                seg = (ax, ay, bx, by)
                break
        asked = []
        real_walkable = pre.walkable
        pre.walkable = lambda x, y: (asked.append((x, y)),
                                     real_walkable(x, y))[1]
        pre.clip(*seg)
        clip_pts = list(asked)
        asked.clear()
        pre._sightline(*seg)
        sight_pts = list(asked)
        del pre.walkable
        check(sorted(clip_pts) == sorted(sight_pts) and len(clip_pts) > 8,
              "_sightline samples exactly the points clip() samples",
              f"{len(clip_pts)} points on a {math.dist(seg[:2], seg[2:]):.0f} "
              f"unit segment")
        # ... and the comparison above is only a check if it can refuse. A
        # reordering that dropped every other sample is the fast wrong answer.
        check(sorted(clip_pts) != sorted(sight_pts[::2]),
              "that comparison refuses a line test that skips samples",
              f"{len(sight_pts[::2])} of {len(clip_pts)} would have passed")
        check(clip_pts != sight_pts,
              "and the ORDER really is different, so the saving is real",
              f"first sample {sight_pts[0] != clip_pts[0]} differs")

        # (b) the verdict, over real segments, with both answers present.
        agree = vis_yes = vis_no = 0
        for _ in range(1200):
            ax, ay = rng10.choice(pre.trapezoids).centre
            ang, d = rng10.uniform(0, 2 * math.pi), rng10.uniform(50.0, 2500.0)
            bx, by = ax + math.cos(ang) * d, ay + math.sin(ang) * d
            want = pre.clip(ax, ay, bx, by) == (bx, by)
            got = pre._visible(ax, ay, bx, by)
            agree += (want == got)
            vis_yes += bool(want)
            vis_no += (not want)
        check(agree == 1200, "_visible agrees with clip() on every segment",
              f"{agree}/1200")
        check(vis_yes > 50 and vis_no > 50,
              "and both answers occurred, so that was not one answer repeated",
              f"{vis_yes} visible, {vis_no} blocked")

        # (c) walkable() is now a SECOND point test, over a 2-D bucket of flat
        #     floats; containing() still runs the first one over Trapezoid
        #     objects. They must agree everywhere, which is a claim the geometry
        #     can refute -- and does, if the bucketing loses a trapezoid whose
        #     x span straddles a cell edge.
        wxs = [v for t in pre.trapezoids
               for v in (t.x_bottom_left, t.x_top_right)]
        wys = [v for t in pre.trapezoids for v in (t.y_bottom, t.y_top)]
        hit = miss = disagree = 0
        for _ in range(120000):
            x = rng10.uniform(min(wxs) - 600.0, max(wxs) + 600.0)
            y = rng10.uniform(min(wys) - 600.0, max(wys) + 600.0)
            w = pre.walkable(x, y)
            if w != bool(pre.containing(x, y)):
                disagree += 1
            hit += bool(w)
            miss += (not w)
        check(disagree == 0,
              "walkable() and containing() agree on every point",
              f"{disagree} of 120,000 disagree")
        check(hit > 1000 and miss > 1000,
              "and both answers occurred over the sample",
              f"{hit} walkable, {miss} not")

        # -- the sweep ---------------------------------------------------
        pairs = chase_pairs(pre, args.routes)
        print(f"    {len(pairs)} pairs, {CHASE_LO:.0f}..{CHASE_HI:.0f} units "
              f"apart, on a {TICK_MS:.0f} ms tick")
        with as_before(pre):
            before_ms, before_paths = sweep(pre, pairs)
        after_ms, after_paths = sweep(pre, pairs)
        over_before = latency_table("BEFORE", before_ms)
        over_after = latency_table("AFTER", after_ms)

        # (d) the component pre-check answers None without searching. It may
        #     only do that where the search would have failed anyway, so every
        #     pair it short-circuits must be one the pre-fix code also refused.
        skipped = wrong = 0
        comp = pre._component
        for k, (ax, ay, bx, by) in enumerate(pairs):
            starts, goals = pre.containing(ax, ay), pre.containing(bx, by)
            if not starts or not goals:
                continue
            si = pre._flat_index(starts[0])
            gset = {pre._flat_index(g) for g in goals}
            if si in gset:
                continue
            if all(comp[g] != comp[si] for g in gset):
                skipped += 1
                if before_paths[k] is not None:
                    wrong += 1
        check(wrong == 0,
              "every route the component pre-check skips was already None",
              f"{skipped} skipped, {wrong} of them had a path before")
        check(skipped > 0,
              "and it skipped some, so that was not a vacuous claim",
              f"{skipped} of {len(pairs)}")

        # (e) the four claims that make a faster router safe.
        bad_after = all_valid(pre, after_paths)
        check(bad_after == 0,
              "EVERY path returned passes route()'s own clip gate",
              f"{sum(1 for p in after_paths if p)} paths, {bad_after} bad")
        none_before = sum(1 for p in before_paths if p is None)
        none_after = sum(1 for p in after_paths if p is None)
        check(none_after == none_before,
              "the None rate did not rise",
              f"{none_before} before, {none_after} after")
        differ = sum(1 for a, b in zip(before_paths, after_paths) if a != b)
        check(differ == 0,
              "and not one path differs from what the old code returned",
              f"{differ} of {len(pairs)}")
        ratios = length_ratios(before_paths, after_paths)
        mean_r = sum(ratios) / len(ratios)
        check(mean_r <= LENGTH_MEAN_MAX and max(ratios) <= LENGTH_WORST_MAX,
              f"path length within tolerance (mean <= {LENGTH_MEAN_MAX}, "
              f"worst <= {LENGTH_WORST_MAX})",
              f"mean {mean_r:.6f}, worst {max(ratios):.6f} over {len(ratios)}")
        confirmed = confirmed_over_tick(pre, pairs, after_ms)
        check(not confirmed,
              "no route in the sweep blew a whole 50 ms tick",
              f"{over_after} candidate(s) re-timed, {len(confirmed)} confirmed"
              f"; max {max(after_ms):.1f} ms")
        for k, best in confirmed[:4]:
            print(f"        pair {k}: {best:.1f} ms on the best of 5")
        # The other side of it: without this, a BEFORE reconstruction that had
        # quietly stopped reconstructing anything would make the AFTER numbers
        # look like a victory over nothing.
        #
        # It is a TOTAL rather than a maximum, and that is the whole design.
        # The first version asserted `max(before_ms) > 3 * TICK_MS` and it was
        # wrong in a way worth recording: the pathological pairs are ~1% of the
        # set, so at `--routes 400` the sample does not contain one, the pre-fix
        # worst case reads 108 ms instead of 301, and the check went red in
        # every sabotage run below -- including the one that broke nothing at
        # all, where it was the ONLY red and would have been read as the catch.
        # A check that reddens on sample size is not measuring the sabotage.
        # Totals are stable where maxima are not: MEASURED at 3.77x, 4.20x,
        # 6.14x and 5.98x over 200, 400, 800 and 1,500 pairs.
        ratio = sum(before_ms) / sum(after_ms)
        check(ratio >= 2.5,
              "the pre-fix code was materially slower over the same pairs, so "
              "the fix measured something real",
              f"{sum(before_ms) / 1000.0:.2f} s against "
              f"{sum(after_ms) / 1000.0:.2f} s, {ratio:.2f}x; "
              f"{over_before} of {len(pairs)} over a tick, worst "
              f"{max(before_ms) / TICK_MS:.1f} ticks")

        # (f) THE SABOTAGE, built and run. A router that does not smooth at all
        #     is FASTER than the real one -- so if the timing table were the
        #     whole check, this would read as a further win. It is caught by
        #     length and by nothing else in the timing half.
        real_pull = pre._string_pull
        pre._string_pull = lambda pts, budget=None: list(pts)
        raw_ms, raw_paths = sweep(pre, pairs)
        del pre._string_pull
        latency_table("RAW-SAB", raw_ms)
        raw_ratios = length_ratios(after_paths, raw_paths)
        raw_mean, raw_worst = (sum(raw_ratios) / len(raw_ratios),
                               max(raw_ratios))
        pre._string_pull = lambda pts, budget=None: list(pts)
        raw_confirmed = confirmed_over_tick(pre, pairs, raw_ms)
        del pre._string_pull
        check(not raw_confirmed,
              "SABOTAGE (no smoothing) passes the timing check",
              f"max {max(raw_ms):.1f} ms against the real {max(after_ms):.1f}, "
              f"{len(raw_confirmed)} confirmed over a tick")
        check(raw_mean > LENGTH_MEAN_MAX and raw_worst > LENGTH_WORST_MAX,
              "and is caught by the length check, which is therefore real",
              f"mean {raw_mean:.3f} > {LENGTH_MEAN_MAX}, "
              f"worst {raw_worst:.1f} > {LENGTH_WORST_MAX}")

        # (g) PULL_SAMPLE_BUDGET. It is set above anything measured, so the
        #     sweep above never touched it -- which means the sweep says
        #     nothing about what happens when it does. Force it down and check
        #     the degradation is the one claimed: longer paths, never invalid
        #     ones.
        spend, counter = [], [0]
        real_sight = pre._sightline

        def counting_sightline(*a):
            ok, used = real_sight(*a)
            counter[0] += used
            return ok, used

        def watched_pull(pts, budget=None):
            counter[0] = 0
            out = real_pull(pts, budget)
            spend.append(counter[0])
            return out

        pre._sightline = counting_sightline
        pre._string_pull = watched_pull
        sweep(pre, pairs)
        del pre._sightline
        del pre._string_pull
        check(max(spend) < pathmap.PULL_SAMPLE_BUDGET,
              "nothing in the sweep reaches PULL_SAMPLE_BUDGET",
              f"worst pull spent {max(spend)} of "
              f"{pathmap.PULL_SAMPLE_BUDGET} samples")
        saved_budget = pathmap.PULL_SAMPLE_BUDGET
        try:
            pathmap.PULL_SAMPLE_BUDGET = 20
            tight_ms, tight_paths = sweep(pre, pairs)
        finally:
            pathmap.PULL_SAMPLE_BUDGET = saved_budget
        longer = sum(1 for a, b in zip(after_paths, tight_paths)
                     if a and b and path_length(b) > path_length(a) + 1e-9)
        check(longer > 0,
              "a budget of 20 really does bite, so (g) is not vacuous",
              f"{longer} paths got longer")
        check(all_valid(pre, tight_paths) == 0,
              "and a truncated smoother still returns only walkable paths",
              f"{sum(1 for p in tight_paths if p)} paths, 0 bad")
        check(pathmap.PULL_SAMPLE_BUDGET == saved_budget,
              "the budget was put back", f"{pathmap.PULL_SAMPLE_BUDGET}")

    dt = time.perf_counter() - t0
    print(f"\nwalked the archive in {dt:.1f}s")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
